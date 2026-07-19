"""
GD Copy Engine — Gold Diggers VIP emulation signal generator.

Strategy:
  1. Identify key S/R levels: Asia range (as level source), swing H/L, round numbers
  2. Generate pending limit-zone signals when price approaches a level
  3. Trigger (activate) when price enters the entry zone
  4. Monitor outcomes; move SL to BE after TP1; learn from results
  5. Continuously correlate our signals with actual GD VIP signals to
     benchmark accuracy — goal is to fire BEFORE GD VIP (negative lead time)

Session: 04:00-16:00 UTC — measured from 591 real GD VIP signals: 23% arrive
  04:00-06:59 (late-Asia push on the Asia range), 72% 07:00-14:59, 5% after
  15:00. Asia range is used as a level source (not a trading session).
Signal expiry: 2 hours (matches bounce engine)

Lead time (correlation_time_delta_s) is SIGNED:
  negative = we fired first (good — we predicted the level)
  positive = GD VIP fired first (we lagged)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import logging.handlers
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import forex_trader.config as _cfg_module
from forex_trader.gd_copy_signal import database as gdc_db
from forex_trader.gd_copy_signal import level_detector as ld
from forex_trader.gd_copy_signal import ml_engine as gdc_ml
from forex_trader.gd_copy_signal import signal_generator as sg

_log = logging.getLogger("gd_copy_signal")


def _setup_logger() -> None:
    """Attach a rotating file handler to the gd_copy_signal logger."""
    try:
        data_dir = Path(_cfg_module.DATA_DIR)
        log_path = data_dir / "gd_copy_signal.log"
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in _log.handlers):
            h = logging.handlers.RotatingFileHandler(
                str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3
            )
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s — %(message)s"
            ))
            _log.addHandler(h)
            _log.setLevel(logging.DEBUG)
    except Exception:
        pass

# ── Constants ──────────────────────────────────────────────────────────────────
_CYCLE_INTERVAL_S     = 60      # main cycle: 1 minute
_OUTCOME_INTERVAL_S   = 5       # outcome/trigger loop
_CORR_INTERVAL_S      = 30      # correlation check loop
_SIGNAL_MAX_AGE_S     = 7200    # 2-hour pending expiry
_LEVEL_COOLDOWN_S     = 1800    # 30 min before same level re-signals
_MAX_OPEN_SIGNALS     = 3       # cap concurrent open positions
_ML_BLOCK_THRESHOLD   = 0.0     # block live execution if predicted R-multiple < 0
_CONSEC_LOSS_LIMIT    = 3       # consecutive same-direction losses → cooldown
_CONSEC_LOSS_WINDOW   = 7200    # 2-hour window for consecutive-loss check
# Correlation semantics: our signal PREDICTS a VIP signal when the VIP entry
# arrives at the same level while our pending signal is still alive. We create
# zone signals as price APPROACHES a level; VIP posts when price ARRIVES — so
# legitimate matches routinely lead by 10-30 minutes (near-miss data: 498 of
# 511 direction+price matches failed only on the old symmetric ±300s window,
# with avg lead -836s and avg price distance 1.1pts). The window is therefore
# asymmetric: we may lead by up to the signal lifetime, or lag by 5 minutes
# (Telegram delivery latency).
_VIP_CORR_LEAD_MAX_S  = _SIGNAL_MAX_AGE_S  # we fired first: up to 2h (signal lifetime)
_VIP_CORR_LAG_MAX_S   = 300     # VIP fired first: 5 min grace (delivery latency)
_VIP_CORR_PRICE_DELTA = 3.0     # pts between entry-zone midpoints (zones are 3-4pts wide)

# Lot size for virtual P&L tracking (not live yet)
_VIRTUAL_LOT = 0.1
_POINT_VALUE = 1.0   # $ per point per 0.01 lot → 0.01 * 100 = $1/point at 0.1 lot

_LIVE_MISSING_THRESHOLD = 3   # consecutive get_positions() misses before treating a live ticket as closed

# ── Singleton ─────────────────────────────────────────────────────────────────
_instance: Optional["GDCopyEngine"] = None


def get_instance() -> Optional["GDCopyEngine"]:
    return _instance


def init(bridge) -> "GDCopyEngine":
    global _instance
    if _instance is None:
        _setup_logger()
        _instance = GDCopyEngine(bridge)
    return _instance


class GDCopyEngine:
    def __init__(self, bridge):
        self._bridge    = bridge
        self._main_eng  = None
        self.is_running = False
        self._tasks:    list[asyncio.Task] = []
        self._refresh_cbs: list[Callable] = []
        self._last_cycle_ts: Optional[float] = None
        self._status_msg = "Stopped"

        # Cached market state from last cycle
        self._cached: dict = {
            "price":    0.0,
            "atr":      8.0,
            "adx":      0.0,
            "htf_bias": "neutral",
            "h1_bias":  "neutral",
            "session":  "off",
            "levels":   [],
        }

        # Debounce for _reconcile_live_signal — a ticket missing from
        # get_positions() can be a transient bridge hiccup, not a real close.
        self._live_missing_streak: dict[int, int] = {}

    def set_main_engine(self, engine) -> None:
        self._main_eng = engine

    def add_refresh_callback(self, cb: Callable) -> None:
        self._refresh_cbs.append(cb)

    def _notify_refresh(self) -> None:
        for cb in self._refresh_cbs:
            try:
                cb()
            except Exception:
                pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._status_msg = "Running"
        gdc_db.set_config("gdc_user_stopped", "0")
        loop = asyncio.get_event_loop()
        self._tasks = [
            loop.create_task(self._cycle_loop()),
            loop.create_task(self._outcome_loop()),
            loop.create_task(self._correlation_loop()),
        ]
        _log.info("[GDC-Engine] started")

    def stop(self, persist: bool = True) -> None:
        self.is_running = False
        self._status_msg = "Stopped"
        if persist:
            # Only write when the user explicitly stops — app shutdown calls
            # stop(persist=False) so the preference survives across restarts.
            gdc_db.set_config("gdc_user_stopped", "1")
        for t in self._tasks:
            t.cancel()
        self._tasks = []
        _log.info("[GDC-Engine] stopped (persist=%s)", persist)

    # ── Main cycle ────────────────────────────────────────────────────────────

    async def _cycle_loop(self) -> None:
        """60-second main loop: detect levels, generate signals."""
        while self.is_running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.warning("[GDC-Engine] cycle error: %s", exc)
            await asyncio.sleep(_CYCLE_INTERVAL_S)

    async def _run_cycle(self) -> None:
        self._last_cycle_ts = time.time()

        # Centralized signal generation (Settings > Remote Node): once this
        # VPS is the active trader and generation has moved to the Mac, skip
        # the whole analysis cycle rather than running it and having its
        # eventual open_trade() call just get forwarded/rejected — this is
        # what actually saves the CPU on the VPS.
        from forex_trader.core import database as _db_module
        if await _db_module.to_db_thread(_db_module.is_remote_node):
            self._status_msg = "Remote/VPS node — signal generation is local-node-only"
            return
        if not await _db_module.to_db_thread(_db_module.should_generate_signals_here):
            self._status_msg = "Centralized mode: generation runs on the local node"
            return

        now_utc = datetime.now(timezone.utc)
        utc_hour = now_utc.hour

        # Session gate — was a hardcoded 00:00-16:00 UTC window (measured
        # GD VIP posting hours), which fought the user-facing
        # Trading Markets toggles (Settings > Strategy): a session the user
        # explicitly enabled could still be silently skipped, and a session
        # they'd disabled could still generate outside that window. Now uses
        # the same is_session_allowed() gate every other engine's real
        # execution respects, so Asia/London/NY on/off is the single source
        # of truth for whether this engine analyses at all.
        _sess_ok, _sess_name = await _db_module.to_db_thread(_db_module.is_session_allowed)
        if not _sess_ok:
            self._status_msg = f"Session '{_sess_name}' not enabled in Trading Markets"
            gdc_db.log_analysis({
                "result": "session_closed",
                "reason": f"Session '{_sess_name}' (UTC {utc_hour:02d}:xx) not enabled in Trading Markets",
            })
            return

        # Fetch candles
        try:
            h1_candles  = await self._bridge.get_candles("H1", 50)
            # 80 bars (~20h) rather than the old 20 -- the GD2/Unicorn
            # detector (ict_patterns.find_unicorn_setup) needs real lookback
            # for its structure-shift and breaker-block checks, validated
            # against live history at 60+ bars.
            m15_candles = await self._bridge.get_candles("M15", 80)
            tick        = await self._bridge.get_tick()
        except Exception as exc:
            _log.debug("[GDC-Engine] candle fetch error: %s", exc)
            self._status_msg = "MT5 bridge offline"
            return

        if not tick or not h1_candles:
            self._status_msg = "No price data"
            return

        price = float(tick.mid or tick.bid or 0)
        if price <= 0:
            return

        # Market context
        atr     = self._calc_atr(m15_candles or h1_candles)
        adx     = self._calc_adx(h1_candles)
        htf     = ld.get_htf_bias(h1_candles)
        session = ld.get_session(utc_hour)

        self._cached.update({
            "price":    price,
            "atr":      atr,
            "adx":      adx,
            "htf_bias": htf,
            "session":  session,
        })

        # ATR gate — don't signal in dead/flash-crash markets
        if atr < 2.0 or atr > 80.0:
            self._status_msg = f"ATR gate: {atr:.1f}"
            return

        # Open position cap
        open_sigs = gdc_db.get_open_signals()
        if len(open_sigs) >= _MAX_OPEN_SIGNALS:
            self._status_msg = f"Cap: {len(open_sigs)} open signals"
            return

        # Get candidate levels
        candidates = ld.get_candidate_levels(h1_candles, price, htf_bias=htf, m15_candles=m15_candles)
        self._cached["levels"] = candidates

        if not candidates:
            self._status_msg = "No candidate levels near price"
            gdc_db.log_analysis({
                "ts": time.time(), "session": session, "htf_bias": htf,
                "price": price, "atr": atr, "adx": adx,
                "result": "no_levels",
            })
            return

        context = {
            "atr":            atr,
            "adx":            adx,
            "htf_bias":       htf,
            "h1_bias":        htf,  # use H1 as proxy
            "session":        session,
            "price_at_signal": price,
        }

        # Deactivate stale levels
        gdc_db.deactivate_old_levels()

        # Touch-track every candidate level type seen this cycle (matched or not) —
        # builds the true denominator for vip_match_rate_for_type.
        for level in candidates:
            gdc_ml.record_level_touch(level["type"])

        cadence = await self._vip_cadence_stats()

        signal_created = False
        for level in candidates:
            if level["score"] < 0.50:
                continue
            direction = level["direction"]

            # Bias filter: strong bias override — don't fight it
            if htf == "bullish" and direction == "SELL" and level["score"] < 0.75:
                continue
            if htf == "bearish" and direction == "BUY" and level["score"] < 0.75:
                continue

            # Per-level cooldown
            if self._level_on_cooldown(level["price"], direction):
                continue

            # Don't duplicate same direction+level already open
            if self._already_open(direction, level["price"]):
                continue

            # Consecutive-loss direction cooldown
            try:
                _cl_cutoff = time.time() - _CONSEC_LOSS_WINDOW
                with gdc_db._conn() as _cl_con:
                    _cl_rows = _cl_con.execute(
                        "SELECT outcome FROM gdc_signals "
                        "WHERE direction=? AND close_time>? AND outcome IN ('win','loss','be') "
                        "ORDER BY close_time DESC LIMIT ?",
                        (direction, _cl_cutoff, _CONSEC_LOSS_LIMIT),
                    ).fetchall()
                _cl_outcomes = [r[0] for r in _cl_rows]
                if len(_cl_outcomes) >= _CONSEC_LOSS_LIMIT and all(o == "loss" for o in _cl_outcomes):
                    _log.info("[GDC-Engine] %s cooldown: %d consec losses in 2h", direction, _CONSEC_LOSS_LIMIT)
                    continue
            except Exception:
                pass

            # Cross-engine conflict suppression
            try:
                from forex_trader.core import database as _cdb_cf
                if _cdb_cf.has_conflict_on_bus("gd_copy", direction, window_seconds=180.0):
                    _log.info("[GDC-Engine] %s suppressed — cross-engine conflict", direction)
                    continue
            except Exception:
                pass

            # Build and store signal
            sig_data = sg.build_signal(level, direction, context)
            sig_data["strategy"] = self._active_strategy()
            sig_id   = gdc_db.create_signal(sig_data)
            if not sig_id:
                continue

            # Inject contextual ML features
            try:
                from forex_trader.core.news_calendar import get_news_proximity_norm as _get_news
                sig_data["news_proximity_norm"] = _get_news()
            except Exception:
                sig_data["news_proximity_norm"] = 1.0
            try:
                from forex_trader.core import database as _cdb_feat
                sig_data["regime_score"]         = _cdb_feat.get_regime_score(context.get("adx", 0), context.get("atr", 5))
                sig_data["equity_drawdown_pct"]  = _cdb_feat.get_equity_drawdown_pct()
                sig_data["concurrent_agreement"] = _cdb_feat.get_concurrent_agreement("gd_copy", direction)
            except Exception:
                sig_data.setdefault("regime_score", 0.5)
                sig_data.setdefault("equity_drawdown_pct", 0.0)
                sig_data.setdefault("concurrent_agreement", 0.0)
            try:
                sig_data["vip_discipline_score"], sig_data["vip_aggression_score"] = \
                    gdc_ml.get_daily_research_scores()
            except Exception:
                sig_data.setdefault("vip_discipline_score", 0.5)
                sig_data.setdefault("vip_aggression_score", 0.5)

            # Write to shared signal bus
            try:
                from forex_trader.core import database as _cdb_bus
                _cdb_bus.write_signal_bus(
                    "gd_copy", direction,
                    confidence=float(level.get("score", 0.5)),
                    signal_id=sig_id,
                )
            except Exception:
                pass

            # ML features + prediction
            prob = None
            win_rate = gdc_db.get_recent_win_rate(20)
            sig_data["minutes_since_last_vip"] = cadence[0]
            sig_data["vip_signals_today"]      = cadence[1]
            feats = gdc_ml.extract_features(sig_data, win_rate)
            if feats:
                gdc_db.store_ml_features(sig_id, feats)
                prob = gdc_ml.predict(feats)
                if prob is not None:
                    gdc_db.store_ml_prob(sig_id, prob)

            # Track level
            gdc_db.upsert_level(
                level["type"], level["price"], direction,
                source="engine",
                notes=f"score={level['score']:.2f} atr={atr:.1f}"
            )

            # Update daily correlation tally (signal already in DB, no +1)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            gdc_db.upsert_daily_correlation(today, gdc_signals_sent=gdc_db.count_today_signals())

            _log.info(
                "[GDC-Engine] SIGNAL %s %s %s level=%.2f score=%.2f ml_prob=%s",
                sig_data["signal_ref"], direction, level["type"],
                level["price"], level["score"],
                f"{prob:.2f}" if prob is not None else "?",
            )

            signal_created = True
            self._notify_refresh()
            break  # one signal per cycle

        if not signal_created:
            top = candidates[0] if candidates else {}
            self._status_msg = (
                f"Top level {top.get('price', 0):.0f} "
                f"({top.get('type', '?')}, score={top.get('score', 0):.2f}) — "
                f"no signal this cycle"
            )
        else:
            self._status_msg = "Signal created"

        gdc_db.log_analysis({
            "ts": time.time(), "session": session, "htf_bias": htf,
            "price": price, "atr": atr, "adx": adx,
            "levels": [{"p": l["price"], "t": l["type"], "s": l["score"]}
                       for l in candidates[:4]],
            "result": "signal" if signal_created else "no_signal",
        })

    # ── Outcome loop ──────────────────────────────────────────────────────────

    async def _outcome_loop(self) -> None:
        """5-second loop: monitor active signals, move SL, close on TP/SL, expire old."""
        while self.is_running:
            try:
                await self._check_outcomes()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.debug("[GDC-Engine] outcome error: %s", exc)
            await asyncio.sleep(_OUTCOME_INTERVAL_S)

    def _realistic_fill(self, tick, direction: str, closing: bool) -> float:
        """Approximate a real MT5 fill price: buys fill at ask, sells at bid.
        closing=True means we're exiting the position (opposite side of entry)."""
        buy_side = (direction == "BUY") != closing
        return float(tick.ask if buy_side else tick.bid) or float(tick.mid or 0)

    def _net_pnl(self, sig: dict, pnl_pts: float, exit_tick) -> tuple[float, float]:
        """(gross_pnl_dollars, net_pnl_dollars) after spread/commission/slippage,
        using the same fee model as real GD VIP trades on the main engine."""
        gross = pnl_pts * _VIRTUAL_LOT * 100
        if self._main_eng is None:
            return gross, gross
        try:
            hold_hours = (time.time() - float(sig.get("trigger_time") or sig.get("created_at", time.time()))) / 3600.0
            spread = float(getattr(exit_tick, "spread", 0.0) or 0.0)
            costs = self._main_eng.calculate_fees(_VIRTUAL_LOT, spread, hold_hours)
            net = gross - costs["total_cost"]
            return round(gross, 4), round(net, 4)
        except Exception:
            return gross, gross

    async def _check_outcomes(self) -> None:
        try:
            tick = await self._bridge.get_tick()
            if not tick:
                return
            price = float(tick.mid or tick.bid or 0)
            if price <= 0:
                return
        except Exception:
            return

        open_sigs = gdc_db.get_open_signals()
        now = time.time()

        for sig in open_sigs:
            sig_id    = sig["id"]
            status    = sig["status"]
            direction = sig["direction"]
            entry_lo  = sig["entry_low"]
            entry_hi  = sig["entry_high"]
            sl        = sig["stop_loss"]
            tp1       = sig["tp1"]
            # GD2/Unicorn signals only ever carry tp1/tp2/tp3 (see
            # signal_generator.calculate_gd2_tp_structure — 1R partial, 2R
            # partial+BE, 6R runner), not the VIP 8-level ladder, so they
            # need their own mapping rather than falling through the VIP
            # tp4/tp7 lookups (which would otherwise resolve to None and
            # leave a GD2 signal that can never reach its "final" branch).
            if sig.get("strategy") == "gd2_unicorn":
                tp_mid = sig.get("tp2") or tp1
                tp7    = sig.get("tp3") or tp1
            else:
                tp_mid = sig.get("tp4") or sig.get("tp3") or tp1   # mid-ladder partial
                tp7    = sig.get("tp7") or sig.get("tp8") or tp1
            entry_mid = (entry_lo + entry_hi) / 2
            entry_ref = float(sig.get("trigger_price") or entry_mid)  # realistic fill once triggered
            be_moved  = bool(sig.get("sl_moved_to_be", 0))
            created   = float(sig.get("created_at", 0))
            remaining = float(sig.get("remaining_frac") if sig.get("remaining_frac") is not None else 1.0)
            partial_booked = float(sig.get("partial_pnl_dollars") or 0.0)

            # Expire old pending signals
            if status == "pending" and (now - created) > _SIGNAL_MAX_AGE_S:
                gdc_db.expire_signal(sig_id, "max_age_exceeded")
                _log.info("[GDC-Engine] signal %s expired (>2h pending)", sig["signal_ref"])
                self._notify_refresh()
                continue

            # Pending → trigger when price enters zone
            if status == "pending":
                if entry_lo <= price <= entry_hi:
                    fill = self._realistic_fill(tick, direction, closing=False)
                    gdc_db.trigger_signal(sig_id, fill)
                    _log.info(
                        "[GDC-Engine] TRIGGERED %s @ %.2f (fill, mid=%.2f)",
                        sig.get("signal_ref", sig_id), fill, price
                    )
                    # Optionally execute live trade
                    await self._try_live_execute(sig, fill, tick)
                    self._notify_refresh()
                continue

            # Triggered: monitor SL / TP
            if status != "triggered":
                continue

            # Orphan watchdog: live execution was on at trigger time but
            # live_exec_status was never written (crash/restart mid-execute).
            trigger_time = float(sig.get("trigger_time") or 0)
            if (trigger_time > 0
                    and not sig.get("live_exec_status")
                    and (now - trigger_time) > 120):
                gdc_db.update_live_exec(
                    sig_id, status="failed:orphaned_no_response"
                )
                _log.warning(
                    "[GDC-Engine] signal %s triggered %ds ago but live_exec_status "
                    "never written — marking orphaned",
                    sig.get("signal_ref", sig_id), int(now - trigger_time),
                )

            # A real MT5 trade exists for this signal — its outcome/P&L is
            # driven entirely by that trade's actual result, never by the
            # tick-based simulation below. The real trade is managed
            # independently by the main engine's own strategy (SL moves,
            # partials, trailing), which routinely diverges completely from
            # the simulated hit_sl/hit_tp1/... ladder here — confirmed live:
            # simulated P&L bore no relation to real P&L, and in several
            # cases even had the opposite sign (a real win recorded as a
            # simulated loss/breakeven). See _reconcile_live_signal.
            if sig.get("mt5_ticket") and sig.get("live_exec_status") == "executed":
                await self._reconcile_live_signal(sig)
                continue

            # ── VIP-style ladder scale-out ──────────────────────────────────
            # The old logic moved SL to raw entry at TP1 and only counted a
            # "win" at TP7 — 88 of 118 TP1-hitting signals closed 'be' with $0
            # banked, tanking both the reported win rate and the ML labels.
            # GD VIP itself calls TP1 a win; we bank 33% there, 33% at the
            # mid-ladder TP, and let 34% ride to TP7.
            if direction == "BUY":
                hit_sl    = price <= sl
                hit_tp1   = price >= tp1 and remaining >= 1.0 - 1e-6
                hit_mid   = (tp_mid and price >= float(tp_mid)
                             and 0.34 < remaining <= 0.67 + 1e-6)
                hit_final = tp7 and price >= float(tp7)
            else:
                hit_sl    = price >= sl
                hit_tp1   = price <= tp1 and remaining >= 1.0 - 1e-6
                hit_mid   = (tp_mid and price <= float(tp_mid)
                             and 0.34 < remaining <= 0.67 + 1e-6)
                hit_final = tp7 and price <= float(tp7)

            # Round-trip cost in points for BE placement (spread + slippage).
            _cost_pts = round((float(tick.ask) - float(tick.bid)) + 0.05, 2)

            def _leg_pts(exit_px: float) -> float:
                return (exit_px - entry_ref) if direction == "BUY" else (entry_ref - exit_px)

            if hit_sl:
                exit_fill = self._realistic_fill(tick, direction, closing=True)
                leg_pts   = _leg_pts(exit_fill)
                gross_leg, net_leg = self._net_pnl(sig, leg_pts, tick)
                gross_leg *= remaining
                net_leg   *= remaining
                total_net = round(partial_booked + net_leg, 2)
                # Outcome by TOTAL realized result — a trade that banked TP1
                # partials before the BE stop is a win, matching VIP accounting.
                if total_net > 0.5:
                    outcome = "win"
                elif total_net < -0.5:
                    outcome = "loss"
                else:
                    outcome = "be"
                gdc_db.close_signal(
                    sig_id, exit_fill, outcome, round(leg_pts, 2),
                    net_pnl_dollars=total_net,
                    pnl_dollars=round(partial_booked + gross_leg, 2),
                    balance_delta=round(net_leg, 2),
                )
                gdc_ml.record_outcome(sig_id, outcome)
                try:
                    from forex_trader.core import database as _cdb_bus_sl
                    _cdb_bus_sl.close_bus_entry("gd_copy", sig_id)
                except Exception:
                    pass
                try:
                    from forex_trader.sync.ledger import push_trade_closed
                    push_trade_closed({
                        "trade_id":    sig.get("signal_ref") or str(sig_id),
                        "engine":      "gd_copy",
                        "direction":   direction,
                        "strategy":    sig.get("strategy", ""),
                        "open_time":   sig.get("created_at"),
                        "close_time":  time.time(),
                        "pnl_dollars": total_net,
                        "outcome":     outcome,
                        "tg_source":   "GD Copy Engine",
                        "mt5_ticket":  sig.get("mt5_ticket"),
                    })
                except Exception as _le:
                    _log.debug("[Ledger] push failed: %s", _le)
                _log.info(
                    "[GDC-Engine] CLOSED %s SL outcome=%s total_net=$%.2f (partials $%.2f + leg $%.2f)",
                    sig.get("signal_ref", sig_id), outcome, total_net, partial_booked, net_leg
                )
                self._notify_refresh()

            elif hit_tp1:
                exit_fill = self._realistic_fill(tick, direction, closing=True)
                leg_pts   = _leg_pts(exit_fill)
                _gross, _net = self._net_pnl(sig, leg_pts, tick)
                leg_net   = round(_net * 0.33, 2)
                gdc_db.book_partial_close(sig_id, leg_net, 0.33, tp_idx=1)
                be_px = round(
                    entry_ref + _cost_pts if direction == "BUY" else entry_ref - _cost_pts, 2
                )
                gdc_db.move_sl_to_be(sig_id, be_price=be_px)
                _log.info(
                    "[GDC-Engine] TP1 hit %s → banked $%.2f (33%%), SL → BE+cost %.2f",
                    sig.get("signal_ref", sig_id), leg_net, be_px
                )
                self._notify_refresh()

            elif hit_mid:
                exit_fill = self._realistic_fill(tick, direction, closing=True)
                leg_pts   = _leg_pts(exit_fill)
                _gross, _net = self._net_pnl(sig, leg_pts, tick)
                leg_net   = round(_net * 0.33, 2)
                gdc_db.book_partial_close(sig_id, leg_net, 0.33, tp_idx=4)
                gdc_db.set_stop_loss(sig_id, float(tp1))   # trail to TP1
                _log.info(
                    "[GDC-Engine] TP4 hit %s → banked $%.2f (33%%), SL → TP1 %.2f",
                    sig.get("signal_ref", sig_id), leg_net, float(tp1)
                )
                self._notify_refresh()

            elif hit_final:
                exit_fill = self._realistic_fill(tick, direction, closing=True)
                leg_pts   = _leg_pts(exit_fill)
                gross_leg, net_leg = self._net_pnl(sig, leg_pts, tick)
                gross_leg *= remaining
                net_leg   *= remaining
                total_net = round(partial_booked + net_leg, 2)
                gdc_db.close_signal(
                    sig_id, exit_fill, "win", round(leg_pts, 2),
                    net_pnl_dollars=total_net,
                    pnl_dollars=round(partial_booked + gross_leg, 2),
                    balance_delta=round(net_leg, 2),
                )
                gdc_ml.record_outcome(sig_id, "win")
                try:
                    from forex_trader.core import database as _cdb_bus_tp
                    _cdb_bus_tp.close_bus_entry("gd_copy", sig_id)
                except Exception:
                    pass
                try:
                    from forex_trader.sync.ledger import push_trade_closed
                    push_trade_closed({
                        "trade_id":    sig.get("signal_ref") or str(sig_id),
                        "engine":      "gd_copy",
                        "direction":   direction,
                        "strategy":    sig.get("strategy", ""),
                        "open_time":   sig.get("created_at"),
                        "close_time":  time.time(),
                        "pnl_dollars": total_net,
                        "outcome":     "win",
                        "tg_source":   "GD Copy Engine",
                        "mt5_ticket":  sig.get("mt5_ticket"),
                    })
                except Exception as _le:
                    _log.debug("[Ledger] push failed: %s", _le)
                _log.info(
                    "[GDC-Engine] TP7 hit %s total_net=$%.2f (partials $%.2f + runner $%.2f)",
                    sig.get("signal_ref", sig_id), total_net, partial_booked, net_leg
                )
                self._notify_refresh()

    async def _reconcile_live_signal(self, sig: dict) -> None:
        """Mirror a live-executed signal's outcome/P&L from the real MT5
        trade rather than the tick-based simulation used for virtual
        signals — see the call site in _check_outcomes for why this exists.

        A ticket missing from get_positions() closes the position, but a
        single miss can be a transient bridge hiccup (same debounce pattern
        as core.engine._sync_closed_mt5_positions), so this requires
        _LIVE_MISSING_THRESHOLD consecutive misses before treating the
        signal as actually closed.
        """
        sig_id = sig["id"]
        ticket = int(sig["mt5_ticket"])
        try:
            live_positions = await self._bridge.get_positions()
        except Exception as exc:
            _log.debug("[GDC-Engine] live reconcile: get_positions failed ticket=%s: %s", ticket, exc)
            return
        if any(int(p.get("ticket", 0)) == ticket for p in live_positions):
            self._live_missing_streak.pop(ticket, None)
            return  # still open on the real account — nothing to reconcile yet

        streak = self._live_missing_streak.get(ticket, 0) + 1
        self._live_missing_streak[ticket] = streak
        if streak < _LIVE_MISSING_THRESHOLD:
            return

        try:
            deals = await self._bridge.get_position_history(ticket)
        except Exception as exc:
            _log.debug("[GDC-Engine] live reconcile: get_position_history failed ticket=%s: %s", ticket, exc)
            return
        if not deals:
            return  # nothing to reconcile yet — try again next cycle

        direction  = sig["direction"]
        open_type  = 0 if direction == "BUY" else 1
        close_deals = [d for d in deals if d.get("entry") in (1, 2, 3)]
        if not close_deals:
            close_deals = [d for d in deals if d.get("type") != open_type]
        if not close_deals:
            return

        close_price = max(close_deals, key=lambda d: d.get("time", 0)).get("price")
        net_pnl = round(sum(
            float(d.get("profit", 0)) + float(d.get("swap", 0)) + float(d.get("fee", 0))
            for d in close_deals
        ), 2)
        entry_ref = float(sig.get("trigger_price") or ((sig["entry_low"] + sig["entry_high"]) / 2))
        pnl_pts = round(
            (float(close_price) - entry_ref) if direction == "BUY" else (entry_ref - float(close_price)), 2
        ) if close_price else 0.0

        if net_pnl > 0.5:
            outcome = "win"
        elif net_pnl < -0.5:
            outcome = "loss"
        else:
            outcome = "be"

        gdc_db.close_signal(
            sig_id, float(close_price or entry_ref), outcome, pnl_pts,
            net_pnl_dollars=net_pnl, pnl_dollars=net_pnl, balance_delta=net_pnl,
        )
        gdc_ml.record_outcome(sig_id, outcome)
        self._live_missing_streak.pop(ticket, None)
        try:
            from forex_trader.core import database as _cdb_bus_live
            _cdb_bus_live.close_bus_entry("gd_copy", sig_id)
        except Exception:
            pass
        try:
            from forex_trader.sync.ledger import push_trade_closed
            push_trade_closed({
                "trade_id":    sig.get("signal_ref") or str(sig_id),
                "engine":      "gd_copy",
                "direction":   direction,
                "strategy":    sig.get("strategy", ""),
                "open_time":   sig.get("created_at"),
                "close_time":  time.time(),
                "pnl_dollars": net_pnl,
                "outcome":     outcome,
                "tg_source":   "GD Copy Engine",
                "mt5_ticket":  ticket,
            })
        except Exception as _le:
            _log.debug("[Ledger] push failed: %s", _le)
        _log.info(
            "[GDC-Engine] live reconciled %s ticket=%s outcome=%s real_net=$%.2f",
            sig.get("signal_ref", sig_id), ticket, outcome, net_pnl,
        )
        self._notify_refresh()

    # ── Correlation loop ──────────────────────────────────────────────────────

    async def _correlation_loop(self) -> None:
        """30-second loop: match our signals against actual GD VIP signals.
        Lead time is SIGNED: negative = we fired first (goal), positive = we lagged.
        """
        while self.is_running:
            try:
                await self._check_correlation()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.debug("[GDC-Engine] correlation error: %s", exc)
            await asyncio.sleep(_CORR_INTERVAL_S)

    async def _check_correlation(self) -> None:
        """
        Scan recent real signals from BOTH covered channels (Gold Diggers
        VIP and Gold Diggers 2.0 / Institutional) in vantage_tg_signals and
        match them against our recent GDC signals.

        A match is:
          - Same direction
          - Entry zone midpoints within _VIP_CORR_PRICE_DELTA points
          - Time difference within _VIP_CORR_TIME_WINDOW seconds
          - Same channel: a GDC signal only matches real signals from the
            channel it was modelled on (source_channel), never cross-channel.
        """
        _COVERED_CHANNELS = ("Gold Diggers VIP", "GOLD DIGGERS 2.0 ⚡️")
        # Recent real signals from either channel (last 4 hours) — used
        # for the actual matching window.
        cutoff = time.time() - 14400

        def _fetch_vip_data():
            import sqlite3
            from forex_trader.config import get as cfg_get
            db_path = cfg_get("db_path", "")
            if not db_path:
                return None
            con = sqlite3.connect(db_path, timeout=5)
            con.row_factory = sqlite3.Row
            try:
                _ph = ",".join("?" for _ in _COVERED_CHANNELS)
                vip_rows = con.execute(f"""
                    SELECT id, group_name, direction, entry_low, entry_high, parsed_at, status
                    FROM vantage_tg_signals
                    WHERE group_name IN ({_ph})
                    AND direction IN ('BUY','SELL')
                    AND parsed_at > ?
                    ORDER BY parsed_at DESC
                    LIMIT 100
                """, (*_COVERED_CHANNELS, cutoff)).fetchall()
                # True count of real signals received so far *today* (UTC), both
                # channels combined — distinct from vip_rows above, which is only
                # a 4h rolling window used for matching.
                day_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).timestamp()
                vip_today_count = con.execute(f"""
                    SELECT COUNT(*) FROM vantage_tg_signals
                    WHERE group_name IN ({_ph})
                    AND direction IN ('BUY','SELL')
                    AND parsed_at >= ?
                """, (*_COVERED_CHANNELS, day_start)).fetchone()[0]
                return vip_rows, vip_today_count
            finally:
                con.close()

        try:
            # Offloaded to the DB worker thread — see test_signal.engine's
            # _reconcile_live_pnl for why a raw sqlite3.connect() here is a
            # whole-app hazard, not just a slow-task-local one.
            from forex_trader.core import database as _mdb
            _fetch_result = await _mdb.to_db_thread(_fetch_vip_data)
        except Exception as exc:
            _log.debug("[GDC-Engine] VIP fetch error: %s", exc)
            return
        if _fetch_result is None:
            return
        vip_rows, vip_today_count = _fetch_result

        # Build lookup of recent GDC signals (pending/triggered, last 4h)
        gdc_recent = [
            s for s in gdc_db.get_all_signals(limit=50)
            if float(s.get("created_at", 0)) > cutoff
        ]

        today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        predicted = 0
        lead_times: list[float] = []

        for gdc_sig in gdc_recent:
            if gdc_sig.get("correlation_confirmed"):
                continue  # already matched

            gdc_ts      = float(gdc_sig.get("created_at", 0))
            gdc_mid     = (float(gdc_sig.get("entry_low", 0) or 0)
                           + float(gdc_sig.get("entry_high", 0) or 0)) / 2
            gdc_dir     = gdc_sig.get("direction", "")
            gdc_channel = gdc_sig.get("source_channel") or "Gold Diggers VIP"

            for vip in vip_rows:
                # Never cross-correlate a GD2-modelled signal against a real
                # VIP message or vice versa -- each GDC signal is only ever
                # trying to predict the one channel it was built from.
                if vip["group_name"] != gdc_channel:
                    continue

                vip_mid = ((float(vip["entry_low"] or 0) + float(vip["entry_high"] or 0)) / 2)
                if vip_mid <= 0:
                    continue

                # Use parsed_at (already a float unix timestamp) — more reliable
                # than parsing message_ts text which can have format variations.
                vip_ts = float(vip["parsed_at"] or 0)
                if vip_ts <= 0:
                    continue

                time_delta = gdc_ts - vip_ts   # negative = we were first
                dist = abs(gdc_mid - vip_mid)
                # Asymmetric window: our signal may LEAD the VIP post by its
                # whole pending lifetime (we predict the level before price
                # arrives) but only LAG it by the Telegram delivery grace.
                time_ok = -_VIP_CORR_LEAD_MAX_S <= time_delta <= _VIP_CORR_LAG_MAX_S
                matched = (vip["direction"] == gdc_dir
                           and dist <= _VIP_CORR_PRICE_DELTA
                           and time_ok)

                # Near-miss: direction matched but price/time missed the window —
                # log these (within widened tolerance) so thresholds can be tuned
                # empirically against real data instead of guessed constants.
                if (not matched and vip["direction"] == gdc_dir
                        and dist <= _VIP_CORR_PRICE_DELTA * 4
                        and -_VIP_CORR_LEAD_MAX_S * 2 <= time_delta <= _VIP_CORR_LAG_MAX_S * 4):
                    reason = []
                    if dist > _VIP_CORR_PRICE_DELTA:
                        reason.append("price")
                    if not time_ok:
                        reason.append("time")
                    gdc_db.log_near_miss(
                        gdc_signal_id=gdc_sig["id"],
                        vip_signal_id=str(vip["id"]),
                        direction=gdc_dir,
                        time_delta_s=round(time_delta, 1),
                        distance_pts=round(dist, 2),
                        reason="+".join(reason) or "unknown",
                    )

                if matched:

                    gdc_db.update_correlation(
                        sig_id=gdc_sig["id"],
                        vip_signal_id=str(vip["id"]),
                        time_delta_s=round(time_delta, 1),
                        distance_pts=round(dist, 2),
                    )
                    gdc_sig["correlation_confirmed"] = 1  # keep in-memory snapshot in sync for corr_total below

                    if time_delta < 0:  # we fired first — that's the goal
                        predicted += 1

                    # Signed lead time: negative = we led, positive = we lagged
                    lead_times.append(time_delta)

                    # Feed VIP level type back to ML (pattern learning)
                    vip_level_type = self._classify_vip_level(vip_mid)
                    gdc_ml.record_vip_signal(vip_level_type)

                    break  # one VIP match per GDC signal

        # avg_lead_time_s is signed: negative = we're ahead of GD VIP on average
        avg_lead = sum(lead_times) / len(lead_times) if lead_times else None

        # Query actual daily counts from DB rather than from the rolling 4h window.
        # The 4h window ages out confirmed signals within the same day, causing
        # gdc_correlated to be overwritten to 0 once correlations are >4h old.
        corr_total = gdc_db.count_today_correlated()
        today_sent = gdc_db.count_today_signals()
        corr_rate  = corr_total / today_sent if today_sent else 0.0

        gdc_db.upsert_daily_correlation(
            today,
            vip_signals_sent=vip_today_count,
            vip_predicted=predicted,
            gdc_correlated=corr_total,
            avg_lead_time_s=avg_lead,
            correlation_rate=round(corr_rate, 3),
        )

    # ── Live execution ────────────────────────────────────────────────────────

    async def _try_live_execute(self, sig: dict, trigger_price: float, tick=None) -> None:
        """Execute a real MT5 trade if live execution is enabled and ML gate passes."""
        try:
            from forex_trader.core import database as core_db
            rs = core_db.get_risk_settings()
            if not rs.get("gdc_live_execution", 0):
                # Write a status so the orphan watchdog doesn't misfire on healthy
                # virtual signals when live execution is deliberately disabled.
                gdc_db.update_live_exec(sig["id"], status="skipped:live_disabled")
                return

            # Fill-time re-evaluation (2026-07-17) — a pending zone signal can
            # sit anywhere from a couple of minutes to 4h (GD VIP Runner/
            # Adaptive Runner's expiry window) before price actually reaches
            # its entry zone, but until now nothing re-checked the market
            # bias or re-scored the ML prediction against CURRENT conditions
            # before firing — both were trusted exactly as they were at
            # signal creation, however stale. Falls back to the creation-time
            # ml_prob/htf_bias if the refresh itself fails (bridge offline,
            # etc.) rather than skipping the gates entirely.
            fresh_prob = sig.get("ml_prob")
            direction  = sig.get("direction")
            try:
                h1_candles  = await self._bridge.get_candles("H1", 50)
                m15_candles = await self._bridge.get_candles("M15", 80)
                if h1_candles:
                    fresh_htf = ld.get_htf_bias(h1_candles)
                    fresh_atr = self._calc_atr(m15_candles or h1_candles)
                    fresh_adx = self._calc_adx(h1_candles)
                    fresh_session = ld.get_session(datetime.now(timezone.utc).hour)

                    # Bias re-check — the exact same "against-bias needs a
                    # strong level score" rule _run_cycle already applies at
                    # creation time, just re-evaluated against the CURRENT
                    # bias instead of whatever it was when the signal fired.
                    level_score = float(sig.get("level_score", 0.5) or 0.5)
                    if ((fresh_htf == "bullish" and direction == "SELL" and level_score < 0.75)
                            or (fresh_htf == "bearish" and direction == "BUY" and level_score < 0.75)):
                        gdc_db.store_ml_prob_at_fill(sig["id"], fresh_prob or 0.0, fresh_htf)
                        gdc_db.update_live_exec(sig["id"], status="bias_skipped")
                        _log.info(
                            "[GDC-Engine] bias gate blocked live exec %s — htf now %s vs "
                            "direction=%s, level_score=%.2f < 0.75",
                            sig.get("signal_ref"), fresh_htf, direction, level_score,
                        )
                        return

                    # Fresh ML re-score — same feature set ml_engine.
                    # extract_features used at creation, with every dynamic
                    # input (bias/ATR/ADX/session/news/regime/drawdown/
                    # agreement/VIP cadence) recomputed against now instead
                    # of signal-creation time. Static fields (level_type,
                    # level_score, distance, rr_tp1, created_at) are left as
                    # originally captured — those describe the signal itself,
                    # not current conditions.
                    fresh_sig = dict(sig)
                    fresh_sig["htf_bias"] = fresh_htf
                    fresh_sig["h1_bias"]  = fresh_htf
                    fresh_sig["adx"]      = fresh_adx
                    fresh_sig["atr"]      = fresh_atr
                    fresh_sig["session"]  = fresh_session
                    try:
                        from forex_trader.core.news_calendar import get_news_proximity_norm as _get_news
                        fresh_sig["news_proximity_norm"] = _get_news()
                    except Exception:
                        pass
                    try:
                        fresh_sig["regime_score"] = core_db.get_regime_score(fresh_adx, fresh_atr)
                        fresh_sig["equity_drawdown_pct"] = core_db.get_equity_drawdown_pct()
                        fresh_sig["concurrent_agreement"] = core_db.get_concurrent_agreement(
                            "gd_copy", direction)
                    except Exception:
                        pass
                    try:
                        fresh_sig["vip_discipline_score"], fresh_sig["vip_aggression_score"] = \
                            gdc_ml.get_daily_research_scores()
                    except Exception:
                        pass
                    cadence = await self._vip_cadence_stats()
                    fresh_sig["minutes_since_last_vip"] = cadence[0]
                    fresh_sig["vip_signals_today"]      = cadence[1]

                    win_rate = gdc_db.get_recent_win_rate(20)
                    fresh_feats = gdc_ml.extract_features(fresh_sig, win_rate)
                    if fresh_feats:
                        _fp = gdc_ml.predict(fresh_feats)
                        if _fp is not None:
                            fresh_prob = _fp
                    gdc_db.store_ml_prob_at_fill(sig["id"], fresh_prob or 0.0, fresh_htf)
            except Exception as _refresh_exc:
                _log.warning(
                    "[GDC-Engine] fill-time re-evaluation failed for %s, falling back to "
                    "creation-time ml_prob: %s", sig.get("signal_ref"), _refresh_exc,
                )

            # ML gate: block live execution when predicted R-multiple < 0 (expected loss)
            if fresh_prob is not None and float(fresh_prob) < _ML_BLOCK_THRESHOLD:
                gdc_db.update_live_exec(sig["id"], status="ml_skipped")
                _log.info("[GDC-Engine] ML gate blocked live exec (predicted_R=%.3f)", float(fresh_prob))
                return

            if self._main_eng is None:
                return

            # Persist to vantage_signals first — open_trade_from_signal looks up
            # the signal by signal_id, it does not accept a Signal object.
            # Strategy is resolved automatically downstream via the channel
            # override lookup for source_name="GD Copy Engine" (see
            # _active_strategy, which mirrors the same lookup).
            main_sig = self._main_eng.create_signal(
                source_name = "GD Copy Engine",
                direction   = sig["direction"],
                entry_low   = sig["entry_low"],
                entry_high  = sig["entry_high"],
                stop_loss   = sig["stop_loss"],
                tp1         = sig.get("tp1"),
                tp2         = sig.get("tp2"),
                tp3         = sig.get("tp3"),
                tp4         = sig.get("tp4"),
                tp5         = sig.get("tp5"),
                tp6         = sig.get("tp6"),
                tp7         = sig.get("tp7"),
                tp8         = sig.get("tp8"),
                notes       = f"GDC {sig.get('signal_ref', '')} level={sig.get('level_type', '')}",
            )
            vantage_sig_id = main_sig["signal_id"]

            trade = await self._main_eng.open_trade_from_signal(vantage_sig_id, tick=tick)
            if trade:
                gdc_db.update_live_exec(
                    sig["id"],
                    mt5_ticket=trade.get("mt5_ticket"),
                    vantage_sig_id=vantage_sig_id,
                    status="executed",
                )
                _log.info("[GDC-Engine] live trade opened mt5=%s", trade.get("mt5_ticket", "?"))
            else:
                gdc_db.update_live_exec(sig["id"], status="open_failed")

        except Exception as exc:
            _log.warning("[GDC-Engine] live exec error: %s", exc)
            try:
                gdc_db.update_live_exec(sig["id"], status=f"error:{exc}")
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _active_strategy(self) -> str:
        """The strategy actually selected for the GD VIP channel — same one used to
        manage real GD VIP trades — so GDC's virtual outcomes are modelled on the
        same SL/TP management rules, not an unrelated leftover default."""
        try:
            from forex_trader.core import database as core_db
            from forex_trader.core.models import STRATEGY_SCALE_OUT
            override = core_db.get_channel_strategy_override("GD Copy Engine")
            if override and override != "auto":
                return override
            rs = core_db.get_risk_settings()
            return rs.get("trade_strategy", STRATEGY_SCALE_OUT)
        except Exception:
            return "scale_out"

    def _level_on_cooldown(self, price: float, direction: str) -> bool:
        """True if a signal for this level+direction was created within the cooldown window."""
        cutoff = time.time() - _LEVEL_COOLDOWN_S
        recent = gdc_db.get_all_signals(limit=20)
        for s in recent:
            if (s.get("direction") == direction
                    and abs(float(s.get("level_price", 0) or 0) - price) <= 3.0
                    and float(s.get("created_at", 0)) > cutoff):
                return True
        return False

    def _already_open(self, direction: str, level_price: float) -> bool:
        """True if there's already an open signal for this direction+level."""
        for s in gdc_db.get_open_signals():
            if (s.get("direction") == direction
                    and abs(float(s.get("level_price", 0) or 0) - level_price) <= 3.0):
                return True
        return False

    def _today_signal_count(self) -> int:
        """Count of signals created today (UTC). Uses SQL COUNT — not capped by limit."""
        return gdc_db.count_today_signals()

    async def _vip_cadence_stats(self) -> tuple[float, int]:
        """(minutes_since_last_real_vip_signal, vip_signals_received_today).
        Feeds the ML cadence features so the model can learn GD VIP's posting
        rhythm (e.g. quiet for 3h+ → higher chance one is "due") instead of
        relying purely on static level geometry."""
        def _fetch():
            import sqlite3
            from forex_trader.config import get as cfg_get
            db_path = cfg_get("db_path", "")
            if not db_path:
                return None
            con = sqlite3.connect(db_path, timeout=5)
            con.row_factory = sqlite3.Row
            try:
                last_row = con.execute("""
                    SELECT parsed_at FROM vantage_tg_signals
                    WHERE group_name='Gold Diggers VIP' AND direction IN ('BUY','SELL')
                    ORDER BY parsed_at DESC LIMIT 1
                """).fetchone()
                day_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).timestamp()
                today_count = con.execute("""
                    SELECT COUNT(*) FROM vantage_tg_signals
                    WHERE group_name='Gold Diggers VIP' AND direction IN ('BUY','SELL')
                    AND parsed_at >= ?
                """, (day_start,)).fetchone()[0]
                return (last_row["parsed_at"] if last_row else None), today_count
            finally:
                con.close()

        try:
            # Offloaded to the DB worker thread — see _check_correlation.
            from forex_trader.core import database as _mdb
            _result = await _mdb.to_db_thread(_fetch)
        except Exception as exc:
            _log.debug("[GDC-Engine] cadence stats error: %s", exc)
            return 240.0, 0
        if _result is None:
            return 240.0, 0
        last_parsed_at, today_count = _result
        mins_since = (time.time() - last_parsed_at) / 60.0 if last_parsed_at else 240.0
        return mins_since, today_count

    def _classify_vip_level(self, price: float) -> str:
        """Heuristic: classify a VIP signal's level type for pattern learning."""
        if price <= 0:
            return "unknown"
        nearest_10 = round(price / 10) * 10
        if abs(price - nearest_10) < 2:
            return "round_10"
        if abs(price - (nearest_10 + 5)) < 2:
            return "round_5"
        # Compare against known Asia range
        cached_lvls = self._cached.get("levels", [])
        for lvl in cached_lvls:
            if abs(lvl.get("price", 0) - price) < 4:
                return lvl.get("type", "unknown")
        return "swing_high"  # most common for GD VIP BUY signals

    @staticmethod
    def _calc_atr(candles: list[dict], period: int = 14) -> float:
        """Simple ATR from candle high/low."""
        if not candles or len(candles) < 2:
            return 8.0
        trs = []
        for i in range(1, min(period + 1, len(candles))):
            h = float(candles[i].get("high", candles[i].get("h", 0)) or 0)
            l = float(candles[i].get("low",  candles[i].get("l", 0)) or 0)
            pc = float(candles[i-1].get("close", candles[i-1].get("c", 0)) or 0)
            if h > 0 and l > 0:
                trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return round(sum(trs) / len(trs), 2) if trs else 8.0

    @staticmethod
    def _calc_adx(candles: list[dict], period: int = 14) -> float:
        """Simplified ADX (uses ATR-normalised DM average as proxy)."""
        if not candles or len(candles) < period + 1:
            return 25.0
        plus_dms, minus_dms, trs = [], [], []
        for i in range(1, len(candles)):
            h  = float(candles[i].get("high",  candles[i].get("h", 0)) or 0)
            l  = float(candles[i].get("low",   candles[i].get("l", 0)) or 0)
            ph = float(candles[i-1].get("high", candles[i-1].get("h", 0)) or 0)
            pl = float(candles[i-1].get("low",  candles[i-1].get("l", 0)) or 0)
            pc = float(candles[i-1].get("close",candles[i-1].get("c", 0)) or 0)
            if h <= 0 or l <= 0:
                continue
            up_move   = h - ph
            down_move = pl - l
            plus_dm   = up_move   if up_move > down_move and up_move > 0   else 0
            minus_dm  = down_move if down_move > up_move and down_move > 0 else 0
            tr = max(h - l, abs(h - pc), abs(l - pc)) if pc > 0 else (h - l)
            plus_dms.append(plus_dm)
            minus_dms.append(minus_dm)
            trs.append(tr)

        if not trs:
            return 25.0

        atr14  = sum(trs[-period:]) / period
        if atr14 <= 0:
            return 25.0
        plus14  = sum(plus_dms[-period:])  / period
        minus14 = sum(minus_dms[-period:]) / period
        di_plus  = plus14  / atr14 * 100
        di_minus = minus14 / atr14 * 100
        di_sum   = di_plus + di_minus
        if di_sum == 0:
            return 25.0
        dx = abs(di_plus - di_minus) / di_sum * 100
        return round(dx, 1)

    def get_status(self) -> dict:
        return {
            "is_running":     self.is_running,
            "status_msg":     self._status_msg,
            "last_cycle_ts":  self._last_cycle_ts,
            "cached":         self._cached,
        }
