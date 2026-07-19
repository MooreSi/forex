"""
BreakoutEngine — trend-following / breakout signal engine.

Runs automatically alongside the bounce (TestSignal) engine.
NEVER places MT5 orders — virtual tracking only until confidence is established.
NEVER shares data with the bounce engine — separate DB, separate signals, separate ML.

Architecture (mirrors the bounce engine's timing model):
  • M5 candle gate    — main scan every 60s, checks M5 breaks (5-min candles, not 15-min)
  • Velocity monitor  — every 3s, detects live level crosses in real time for break-and-go
  • Outcome checker   — every 5s, TP/SL monitoring for open virtual positions

The velocity monitor is the key improvement for scalping:
  - Tracks tick prices in a 20-second rolling window
  - When price crosses a key level by > min_break_pts with ADX+bias alignment,
    fires a break-and-go signal immediately (seconds after the break, not minutes)
  - Break-and-retest signals still use the M5 candle gate (they need candle confirmation)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import logging.handlers
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import forex_trader.config as cfg_module
from forex_trader.core import ai_provider
from forex_trader.core.dpm_engine import compute_atr

from forex_trader.breakout_signal import database as bdb
from forex_trader.breakout_signal import adaptive_params as ap
from forex_trader.breakout_signal import ml_engine as bo_ml
from forex_trader.breakout_signal.signal_generator import (
    compute_htf_bias,
    compute_h4_bias,
    compute_adx,
    compute_macd_hist,
    identify_key_levels,
    get_session,
    session_is_active,
    is_news_window,
    check_breakout_go,
    check_breakout_retest,
    check_liquidity_sweep,
    calculate_breakout_risk_levels,
)
from forex_trader.breakout_signal.claude_reviewer import review_signal

if TYPE_CHECKING:
    from forex_trader.core.mt5_bridge import MT5BridgeClient

_log = logging.getLogger("breakout_signal")

# ── Timing ────────────────────────────────────────────────────────────────────
_CYCLE_INTERVAL    = 60      # main analysis cycle (M5 candle gate)
_OUTCOME_INTERVAL  = 5       # TP/SL outcome check
_VELOCITY_INTERVAL = 3       # live level-cross monitor
_VELOCITY_WINDOW   = 20      # seconds of price history for velocity
_VELOCITY_COOLDOWN = 90      # seconds before same level can fire again (velocity path)
_LEVEL_COOLDOWN    = 2100    # seconds before same direction+level can fire again (35 min)
_LOT_SIZE          = 0.10
_MAX_SIGNAL_AGE    = 8 * 3600   # expire stale pending signals
_BATCH_REVIEW_EVERY  = 10        # run Claude batch parameter analysis every N closed trades
_BOOTSTRAP_SAMPLES   = 20        # accept all signals while accumulating initial ML training data

# Consecutive-loss direction cooldown: if N or more losses in the same direction
# within the rolling window, suppress that direction until the window clears.
_CONSEC_LOSS_LIMIT  = 3          # consecutive losses before cooldown
_CONSEC_LOSS_WINDOW = 7200       # 2-hour rolling window (seconds)

_instance: Optional["BreakoutEngine"] = None


def get_instance() -> Optional["BreakoutEngine"]:
    return _instance


def init(bridge: "MT5BridgeClient") -> "BreakoutEngine":
    global _instance
    if _instance is None:
        from forex_trader.config import USER_DATA_DIR
        data_dir = USER_DATA_DIR / "data"
        bdb.init(str(data_dir / "breakout_signal.db"))
        bo_ml.init(data_dir)
        _instance = BreakoutEngine(bridge)
    return _instance


class BreakoutEngine:
    def __init__(self, bridge: "MT5BridgeClient"):
        self._bridge = bridge

        # Engine state
        self.is_running    = False
        self.status        = "stopped"
        self.status_detail = ""
        self.last_cycle_at: Optional[float] = None

        # Async tasks
        self._task_cycle:    Optional[asyncio.Task] = None
        self._task_outcome:  Optional[asyncio.Task] = None
        self._task_velocity: Optional[asyncio.Task] = None

        # UI callbacks
        self._refresh_cbs: list[Callable] = []

        # Cached market state — updated by main cycle, read by velocity loop
        self._cached: dict = {
            "key_levels": [],
            "adx":        0.0,
            "htf_bias":   "neutral",
            "h4_bias":    "neutral",
            "atr":        5.0,
            "macd_hist":  0.0,
            "session":    "off",
            "price":      0.0,
        }

        # Velocity loop state
        # (ts, mid_price) ring buffer — 20-second rolling window
        self._price_history: list[tuple[float, float]] = []
        # {f"{direction}:{level:.0f}": last_fired_ts} — cooldown per level
        self._velocity_cooldowns: dict[str, float] = {}

        # Self-learning counters
        self._closed_count:       int   = 0

        # Main engine reference — set by app.py for live MT5 execution
        self._main_engine = None

        self._setup_logger()

    # ── Logger ────────────────────────────────────────────────────────────────

    def _setup_logger(self):
        try:
            data_dir = Path(cfg_module.DATA_DIR)
            log_path = data_dir / "breakout_signal.log"
            if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in _log.handlers):
                h = logging.handlers.RotatingFileHandler(
                    str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3
                )
                h.setFormatter(logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s — %(message)s"
                ))
                _log.addHandler(h)
                _log.setLevel(logging.INFO)
        except Exception:
            pass

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def add_refresh_callback(self, cb: Callable) -> None:
        self._refresh_cbs.append(cb)

    def _notify_refresh(self):
        for cb in self._refresh_cbs:
            try:
                cb()
            except Exception:
                pass

    # ── Live P&L reconciliation ───────────────────────────────────────────────

    async def _reconcile_live_pnl(self) -> None:
        """
        At startup, sync P&L for any closed bo_signal that has an mt5_ticket but
        is showing the virtual simulation figure instead of the actual MT5 profit.
        The conservative strategy manages SL/TP independently of the virtual
        simulation, so its close price and profit can differ significantly.
        """
        try:
            from forex_trader.core import database as _mdb

            def _do_reconcile() -> int:
                import sqlite3 as _sqlite3
                with bdb._conn() as conn:
                    # Also include 'expired' signals that had a live MT5 trade opened —
                    # their position may have been closed externally and the P&L is real.
                    rows = conn.execute(
                        "SELECT id, mt5_ticket, pnl_dollars, outcome, status FROM bo_signals"
                        " WHERE status IN ('closed','expired') AND mt5_ticket IS NOT NULL"
                    ).fetchall()
                if not rows:
                    return 0
                _db_path = _mdb._DB_PATH  # type: ignore[attr-defined]
                main_conn = _sqlite3.connect(f"file:{_db_path}?mode=ro", uri=True)
                main_conn.row_factory = _sqlite3.Row
                updated = 0
                try:
                    for row in rows:
                        sig_id, ticket, sim_pnl, sim_outcome, sig_status = (
                            row[0], row[1], row[2] or 0.0, row[3] or "", row[4] or ""
                        )
                        cur = main_conn.execute(
                            "SELECT mt5_profit, status FROM vantage_simulated_trades"
                            " WHERE mt5_ticket=? AND status='closed'",
                            (ticket,),
                        )
                        main_row = cur.fetchone()
                        if not main_row:
                            continue
                        actual_profit = float(main_row["mt5_profit"] or 0.0)
                        if abs(actual_profit - float(sim_pnl)) < 0.01 and sig_status == "closed":
                            continue  # already correct (skip if not expired+needs closing)
                        mt5_outcome = (
                            "win"  if actual_profit > 1.0  else
                            "loss" if actual_profit < -1.0 else
                            "be"
                        )
                        bdb.update_signal_pnl_from_mt5(sig_id, actual_profit, mt5_outcome)
                        # If this was an expired signal with a live trade, promote it to closed
                        if sig_status == "expired":
                            with bdb._conn() as _c:
                                _c.execute(
                                    "UPDATE bo_signals SET status='closed' WHERE id=?", (sig_id,)
                                )
                            _log.info(
                                "[BO-Engine] Expired live signal %d (ticket %s) promoted to closed: MT5=$%.2f (%s)",
                                sig_id, ticket, actual_profit, mt5_outcome,
                            )
                        if sim_outcome != mt5_outcome:
                            bo_ml.record_outcome(sig_id, mt5_outcome)
                        updated += 1
                        _log.info(
                            "[BO-Engine] Reconciled signal %d (ticket %s): sim=$%.2f → MT5=$%.2f (%s)",
                            sig_id, ticket, sim_pnl, actual_profit, mt5_outcome,
                        )
                finally:
                    main_conn.close()
                return updated

            # Offloaded to the DB worker thread — see test_signal.engine's
            # identical fix for why (raw sqlite3.connect() on the event loop
            # thread blocks the whole app under DB contention, up to 43s
            # observed live).
            updated = await _mdb.to_db_thread(_do_reconcile)
            if updated:
                _log.info("[BO-Engine] Reconciled %d live P&L records with MT5 actuals", updated)
        except Exception as exc:
            _log.warning("[BO-Engine] P&L reconciliation failed: %s", exc)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.is_running:
            return
        # Restore closed-trade count so batch analysis fires at the right interval
        # after a restart, not always starting from 0.
        try:
            self._closed_count = bdb.get_stats().get("closed", 0) % _BATCH_REVIEW_EVERY
        except Exception:
            pass

        # Root-cause fix: the live engine's "conservative" strategy (the global
        # default — core/engine.py _handle_conservative) hardcodes a fixed
        # 5pt SL / 3pt TP1 and explicitly DISCARDS whatever SL/TP1/TP2/TP3 the
        # originating signal computed. That meant every ATR-scaled, level-based
        # stop and every trend-following 1R/1.8R/2.8R target this engine works
        # out was being thrown away and replaced with a tight mean-reversion
        # scalp profile completely unsuited to breakout/trend trades — live
        # data showed the realized avg loss ($49.39) landing almost exactly on
        # the fixed 5pt stop. Pin a per-channel override so Breakout Engine
        # trades use "scale_out" (honors the signal's own tp1/tp2/tp3 with a
        # tiered close) instead, without touching the global default other
        # engines rely on. Only sets it if the user hasn't already chosen an
        # override for this channel.
        try:
            from forex_trader.core import database as _cdb_so
            if _cdb_so.get_channel_strategy_override("Breakout Engine") is None:
                _cdb_so.set_channel_strategy_override("Breakout Engine", "scale_out")
                _log.info(
                    "[BO-Engine] Set live trade strategy override to 'scale_out' "
                    "(was inheriting global default, which discards signal SL/TP)"
                )
        except Exception as _so_exc:
            _log.warning("[BO-Engine] Could not set channel strategy override: %s", _so_exc)
        self.is_running = True
        self.status     = "running"
        self._task_cycle    = asyncio.ensure_future(self._cycle_loop())
        self._task_outcome  = asyncio.ensure_future(self._outcome_loop())
        self._task_velocity = asyncio.ensure_future(self._velocity_loop())
        asyncio.ensure_future(self._reconcile_live_pnl())
        _log.info("[BO-Engine] Started (M5 gate + 3s velocity monitor)")

    def stop(self) -> None:
        self.is_running = False
        self.status     = "stopped"
        for task in (self._task_cycle, self._task_outcome, self._task_velocity):
            if task and not task.done():
                task.cancel()
        _log.info("[BO-Engine] Stopped")

    def set_main_engine(self, engine) -> None:
        """Link to the main SimulationEngine for live MT5 trade execution."""
        self._main_engine = engine

    # ── Main candle-gate loop (every 60s, M5 candles) ────────────────────────

    async def _cycle_loop(self) -> None:
        while self.is_running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _log.exception("[BO-Engine] Cycle error: %s", e)
                self.status_detail = f"Error: {e}"
            await asyncio.sleep(_CYCLE_INTERVAL)

    async def _run_cycle(self) -> None:
        """
        Full analysis cycle — runs every 60s.
        Uses M5 candles for break detection (not M15) so signals are at most 5 minutes
        after a break, not 15 minutes.
        Also refreshes the cached state used by the velocity monitor.
        """
        self.last_cycle_at = time.time()

        # Centralized signal generation (Settings > Remote Node): once this
        # VPS is the active trader and generation has moved to the Mac, skip
        # the whole analysis cycle rather than running it and having its
        # eventual open_trade() call just get forwarded/rejected — this is
        # what actually saves the CPU on the VPS.
        from forex_trader.core import database as _db_module
        if await _db_module.to_db_thread(_db_module.is_remote_node):
            self.status_detail = "Remote/VPS node — signal generation is local-node-only"
            return
        if not await _db_module.to_db_thread(_db_module.should_generate_signals_here):
            self.status_detail = "Centralized mode: generation runs on the local node"
            return

        log_entry: dict = {"ts": time.time()}



        try:
            # ── 1. Market data ────────────────────────────────────────────────
            tick        = await self._bridge.get_tick()
            m5_candles  = await self._bridge.get_candles("M5",  80)   # M5 for break detection
            h1_candles  = await self._bridge.get_candles("H1", 120)   # H1 for HTF bias
            h4_candles  = await self._bridge.get_candles("H4",  40)   # H4 for secondary bias

            if not tick or not m5_candles or not h1_candles:
                self.status_detail = "No market data"
                log_entry.update({"result": "no_data", "suppressed_reason": "No market data"})
                bdb.log_analysis(log_entry)
                return

            # ── 2. Session gate ───────────────────────────────────────────────
            session = get_session()
            log_entry["session"] = session

            if session == "closed":
                log_entry.update({"result": "closed", "suppressed_reason": "Market closed (weekend)"})
                bdb.log_analysis(log_entry)
                return

            # Session gate — was previously generation-in-every-session
            # regardless of the Trading Markets toggles (Settings > Strategy),
            # on the theory that off-session signals still had ML training
            # value. Changed on request: the toggles are now the single
            # source of truth for whether this engine analyses a given
            # session at all, matching GD Copy and Bounce.
            _sess_ok, _sess_name = await _db_module.to_db_thread(_db_module.is_session_allowed)
            if not _sess_ok:
                log_entry.update({
                    "result": "session_disabled",
                    "suppressed_reason": f"Session '{_sess_name}' not enabled in Trading Markets",
                })
                bdb.log_analysis(log_entry)
                self.status_detail = f"Session '{_sess_name}' not enabled in Trading Markets"
                return

            # ── 3. Indicators ─────────────────────────────────────────────────
            current_price = float(tick.ask)
            atr           = compute_atr(m5_candles[-20:], period=14)

            # Dead-market ATR collapse gate: suppress when M5 volatility has
            # collapsed relative to recent baseline.
            if len(m5_candles) >= 50:
                _atr_ref = compute_atr(m5_candles[-50:-10], period=14)
                if _atr_ref > 0:
                    try:
                        from forex_trader.core import database as _cdb_ac
                        _ac_thr = float(_cdb_ac.get_risk_settings().get("atr_collapse_threshold", 0.65))
                    except Exception:
                        _ac_thr = 0.65
                    if atr / _atr_ref < _ac_thr:
                        reason = (
                            f"ATR collapse: {atr:.1f} is {atr/_atr_ref:.0%} of baseline "
                            f"{_atr_ref:.1f} — dead market suppressed"
                        )
                        log_entry.update({"result": "atr_collapse", "suppressed_reason": reason})
                        bdb.log_analysis(log_entry)
                        self.status_detail = reason
                        return

            htf_bias      = compute_htf_bias(h1_candles)
            h4_bias       = compute_h4_bias(h4_candles) if h4_candles else "neutral"
            m5_closes     = [float(c.get("close", 0) or 0) for c in m5_candles]
            adx           = compute_adx(m5_candles[-30:] if len(m5_candles) >= 30 else m5_candles)
            _, macd_hist  = compute_macd_hist(m5_closes)

            log_entry.update({
                "price":    current_price,
                "atr_m15":  atr,     # stored as atr_m15 for schema compat, but is M5 ATR
                "htf_bias": htf_bias,
                "h4_bias":  h4_bias,
                "adx":      round(adx, 1),
            })

            # ── 4. Key levels ─────────────────────────────────────────────────
            key_levels = identify_key_levels(h1_candles, current_price, m15_candles=m5_candles)

            # ── 5. Update velocity cache (always, even if we gate out below) ──
            self._cached.update({
                "key_levels": key_levels[:10],
                "adx":        adx,
                "htf_bias":   htf_bias,
                "h4_bias":    h4_bias,
                "atr":        atr,
                "macd_hist":  macd_hist,
                "session":    session,
                "price":      current_price,
                # Recent closed M5 candles for the velocity path's compression
                # gate (last candle may be forming; _is_compressed excludes
                # nothing here — the 13-candle tail approximates the same
                # 12-candle window the M5 path checks).
                "m5_candles": m5_candles[-13:],
            })

            log_entry["key_levels"] = key_levels[:8]

            # ── 6. ADX gate ───────────────────────────────────────────────────
            min_adx = min(ap.get("min_adx_go"), ap.get("min_adx_retest"))
            if adx < min_adx:
                log_entry.update({
                    "result": "adx_too_low",
                    "suppressed_reason": (
                        f"ADX {adx:.1f} < {min_adx:.0f} — ranging market, "
                        f"not trending enough for breakout"
                    ),
                })
                bdb.log_analysis(log_entry)
                self.status_detail = f"ADX {adx:.1f} — ranging, velocity monitor active"
                return

            # ── 7. Bias gate ──────────────────────────────────────────────────
            if htf_bias == "neutral" and adx < 40:
                log_entry.update({
                    "result": "no_bias",
                    "suppressed_reason": (
                        f"Neutral H1 bias + ADX {adx:.1f} — no directional conviction"
                    ),
                })
                bdb.log_analysis(log_entry)
                return

            # ── 8. Position cap ───────────────────────────────────────────────
            open_sigs = bdb.get_open_signals()
            if len(open_sigs) >= 2:
                log_entry.update({
                    "result": "max_positions",
                    "suppressed_reason": f"Already {len(open_sigs)} open — at position limit",
                })
                bdb.log_analysis(log_entry)
                return

            # ── 9. News window ────────────────────────────────────────────────
            if is_news_window():
                log_entry.update({
                    "result": "news_window",
                    "suppressed_reason": "News window active",
                })
                bdb.log_analysis(log_entry)
                return

            # ── 9b. Spread gate ───────────────────────────────────────────────
            # On gold the spread is 30-50% of a scalp's TP1 distance; a widened
            # spread (Asian thin liquidity, news minutes) silently doubles the
            # cost of every trade taken through it.
            _spread = float(tick.ask) - float(tick.bid)
            _max_spread = ap.get("max_spread_pts")
            if _spread > _max_spread:
                reason = f"Spread {_spread:.2f} > {_max_spread:.2f} limit — entry cost too high"
                log_entry.update({"result": "spread_gate", "suppressed_reason": reason})
                bdb.log_analysis(log_entry)
                self.status_detail = reason
                return

            # ── 10. Break-and-go on M5 (candle close confirmation) ───────────
            context = {
                "adx":       adx,
                "macd_hist": macd_hist,
                "htf_bias":  htf_bias,
                "h4_bias":   h4_bias,
                "session":   session,
                "price":     current_price,
                "atr_m15":   atr,
                "trigger":   "M5_candle",
            }

            # Asian session is thin-liquidity and produced the worst real results
            # (-$412.60 over 26 live trades, the single worst session) — its low
            # volume makes momentum spikes through a level far more likely to be
            # a stop-hunt than the start of a sustained trend leg. Break-and-go
            # chases that spike directly; restrict Asian hours to retest entries
            # only, which require the level to have already been tested and held.
            candidate = None
            if session != "asian":
                candidate = check_breakout_go(
                    m5_candles, key_levels, htf_bias, h4_bias,
                    current_price, atr, adx, macd_hist,
                )
            # ── 11. Break-and-retest (needs candle close confirmation) ────────
            if not candidate:
                candidate = check_breakout_retest(
                    m5_candles, key_levels, htf_bias, h4_bias,
                    current_price, atr, adx, macd_hist,
                )
                if candidate:
                    context["trigger"] = "M5_retest"

            # ── 12. Liquidity-sweep reversal — a wick through a key level that
            # closes back inside is a stop-run, not a break; trade the rejection
            # with the stop beyond the wick. This monetises the exact failed-
            # breakout pattern that caused most 'go'/'retest' losses.
            if not candidate:
                candidate = check_liquidity_sweep(
                    m5_candles, key_levels, htf_bias, h4_bias,
                    current_price, atr, adx, macd_hist,
                )
                if candidate:
                    context["trigger"] = "M5_sweep"

            if not candidate:
                log_entry.update({
                    "result": "no_trigger",
                    "suppressed_reason": (
                        f"ADX {adx:.1f} | {htf_bias} bias — no M5 level break or retest found"
                    ),
                })
                bdb.log_analysis(log_entry)
                self.status_detail = f"ADX {adx:.1f} | {htf_bias} | scanning M5+velocity"
                return

            log_entry["candidate"] = candidate
            await self._process_candidate(candidate, context, log_entry, atr, adx, tick=tick)

        except Exception as exc:
            _log.exception("[BO-Engine] _run_cycle exception: %s", exc)
            log_entry.update({"result": "error", "suppressed_reason": str(exc)})
            try:
                bdb.log_analysis(log_entry)
            except Exception:
                pass

    # ── Velocity monitor (every 3s) — real-time level-cross detection ─────────

    async def _velocity_loop(self) -> None:
        while self.is_running:
            try:
                await self._check_velocity_break()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(_VELOCITY_INTERVAL)

    async def _check_velocity_break(self) -> None:
        """
        Sample the current price every 3 seconds. If price has crossed a key
        level by > min_break_pts within the last 20 seconds, fire a break-and-go
        signal immediately without waiting for the next M5 candle close.

        This is the core improvement for scalping — catches breakouts in real
        time rather than up to 5 minutes later.
        """
        # Only fire if market context is favourable (cached from last cycle)
        cached = self._cached
        if not cached["key_levels"] or cached["adx"] <= 0:
            return

        session = get_session()
        if not session_is_active(session):
            return

        # Velocity is break-and-go only — restrict it out of the thin-liquidity
        # Asian session for the same reason as the M5 gate above (see _run_cycle).
        if session == "asian":
            return

        if is_news_window():
            return

        # Position cap check (cheap DB call)
        open_sigs = bdb.get_open_signals()
        if len(open_sigs) >= 2:
            return

        # Fetch tick
        try:
            tick = await self._bridge.get_tick()
            if not tick:
                return
        except Exception:
            return

        mid   = (float(tick.bid) + float(tick.ask)) / 2
        now   = time.time()
        cutoff = now - _VELOCITY_WINDOW

        # Update rolling price buffer
        self._price_history.append((now, mid))
        self._price_history = [(t, p) for t, p in self._price_history if t >= cutoff]

        if len(self._price_history) < 4:
            return

        oldest_price = self._price_history[0][1]
        adx          = cached["adx"]
        htf_bias     = cached["htf_bias"]
        h4_bias      = cached["h4_bias"]
        atr          = cached["atr"]
        macd_hist    = cached["macd_hist"]
        key_levels   = cached["key_levels"]
        min_break    = ap.get("min_break_pts")
        min_adx_go   = ap.get("min_adx_go")
        dual_bias    = ap.get("require_dual_bias") >= 0.5

        # Same entry-regime gates as the M5 path (2026-07-16 rebuild): reject
        # exhausted trends and non-compressed contexts here too — velocity is
        # just a faster trigger for the same setup, not a licence to chase.
        if adx < min_adx_go or adx > ap.get("max_adx_entry"):
            return

        # Absolute ATR floor: don't fire velocity signals in dead-market conditions.
        if atr < 7.0:
            return

        # Compression gate — uses the M5 candles cached by the last _run_cycle.
        from forex_trader.breakout_signal.signal_generator import _is_compressed
        _m5_cached = cached.get("m5_candles") or []
        if not _is_compressed(_m5_cached, atr, ap.get("compression_max_range_atr")):
            return

        # Check each key level for a live cross
        for level_info in key_levels:
            level    = float(level_info.get("price", 0) or 0)
            ltype    = level_info.get("type", "level")
            strength = int(level_info.get("strength", 1))
            if level <= 0:
                continue

            # ── BUY: price was below level, now above by min_break_pts ────────
            if (htf_bias in ("bullish", "neutral") and
                    (not dual_bias or h4_bias in ("bullish", "neutral")) and
                    macd_hist > 0 and
                    oldest_price < level and
                    mid > level + min_break):

                cooldown_key = f"BUY:{level:.0f}"
                last_fired = self._velocity_cooldowns.get(cooldown_key, 0)
                if now - last_fired < _VELOCITY_COOLDOWN:
                    continue

                if any(s.get("direction") == "BUY" for s in open_sigs):
                    continue

                _log.info(
                    "[BO-Velocity] BUY break detected: price %.2f crossed %.2f "
                    "(was %.2f, +%.1fpts in %.0fs | ADX %.1f)",
                    mid, level, oldest_price, mid - level,
                    now - self._price_history[0][0], adx,
                )
                self._velocity_cooldowns[cooldown_key] = now
                candidate = {
                    "direction":        "BUY",
                    "breakout_type":    "go",
                    "broken_level":     level,
                    "broken_level_type": ltype,
                    "level_strength":   strength,
                    "pts_beyond":       round(mid - level, 2),
                    "trigger":          "velocity",
                }
                context = {
                    "adx":       adx,
                    "macd_hist": macd_hist,
                    "htf_bias":  htf_bias,
                    "h4_bias":   h4_bias,
                    "session":   session,
                    "price":     float(tick.ask),
                    "atr_m15":   atr,
                    "trigger":   "velocity",
                }
                await self._process_candidate(
                    candidate, context, {"ts": now}, atr, adx, velocity=True, tick=tick
                )
                return  # one signal per velocity sweep

            # ── SELL: price was above level, now below by min_break_pts ───────
            if (htf_bias in ("bearish", "neutral") and
                    (not dual_bias or h4_bias in ("bearish", "neutral")) and
                    macd_hist < 0 and
                    oldest_price > level and
                    mid < level - min_break):

                cooldown_key = f"SELL:{level:.0f}"
                last_fired = self._velocity_cooldowns.get(cooldown_key, 0)
                if now - last_fired < _VELOCITY_COOLDOWN:
                    continue

                if any(s.get("direction") == "SELL" for s in open_sigs):
                    continue

                _log.info(
                    "[BO-Velocity] SELL break detected: price %.2f crossed %.2f "
                    "(was %.2f, -%.1fpts in %.0fs | ADX %.1f)",
                    mid, level, oldest_price, level - mid,
                    now - self._price_history[0][0], adx,
                )
                self._velocity_cooldowns[cooldown_key] = now
                candidate = {
                    "direction":        "SELL",
                    "breakout_type":    "go",
                    "broken_level":     level,
                    "broken_level_type": ltype,
                    "level_strength":   strength,
                    "pts_beyond":       round(level - mid, 2),
                    "trigger":          "velocity",
                }
                context = {
                    "adx":       adx,
                    "macd_hist": macd_hist,
                    "htf_bias":  htf_bias,
                    "h4_bias":   h4_bias,
                    "session":   session,
                    "price":     float(tick.bid),
                    "atr_m15":   atr,
                    "trigger":   "velocity",
                }
                await self._process_candidate(
                    candidate, context, {"ts": now}, atr, adx, velocity=True, tick=tick
                )
                return

    # ── Shared candidate processing (M5 gate + velocity both use this) ────────

    async def _process_candidate(
        self,
        candidate: dict,
        context: dict,
        log_entry: dict,
        atr: float,
        adx: float,
        velocity: bool = False,
        tick=None,
    ) -> None:
        """Risk calc → duplicate guard → Claude review → create signal."""

        current_price = context["price"]
        trigger_tag   = "velocity" if velocity else "M5_candle"

        # Toxic-hour block (measured, UTC 12-14 — see core/regime.py) now lives
        # in _execute_live() — it blocks real MT5 orders once
        # hour_blocklist_enabled is on and the
        # current hour is in the blocked set, but signal generation/tracking
        # continues below regardless so the ML model keeps training on live
        # market data from those hours too (previously this returned here
        # unconditionally, meaning nothing was ever created or learned from
        # during a blocked hour — no user-facing on/off control either, just
        # an internal adaptive param defaulting to always-on).

        # ── Broken-level-type filter (measured) ───────────────────────────────
        # Breaks through fvg_bull (37% WR, -$793) and round numbers (36% WR,
        # -$223) lost consistently; breaks of liq_low/ob_bear/fvg_bear were the
        # profitable core (+$675 combined).
        if ap.get("level_filter_enabled") >= 0.5:
            from forex_trader.core.regime import BREAKOUT_BLOCKED_LEVELS
            _blt = candidate.get("broken_level_type", "")
            if _blt in BREAKOUT_BLOCKED_LEVELS:
                _lv_reason = f"Level type '{_blt}' blocked (measured 36-37% WR)"
                if not velocity:
                    log_entry.update({"result": "level_type_blocked", "suppressed_reason": _lv_reason})
                    bdb.log_analysis(log_entry)
                _log.debug("[BO-Engine] %s suppressed: %s", trigger_tag, _lv_reason)
                return

        # Per-level cooldown: prevent re-signalling the same direction+level within 35 min.
        # Prevents the most common failure mode — clustered retries at a level that just failed.
        # Uses DB query so cooldown survives engine restarts.
        try:
            _lc_cutoff = time.time() - _LEVEL_COOLDOWN
            with bdb._conn() as _lc_conn:
                _lc_row = _lc_conn.execute(
                    "SELECT MAX(created_at) FROM bo_signals "
                    "WHERE direction=? AND ROUND(broken_level,0)=ROUND(?,0) AND created_at>?",
                    (candidate["direction"], candidate["broken_level"], _lc_cutoff),
                ).fetchone()
            if _lc_row and _lc_row[0]:
                _mins_ago = int((time.time() - float(_lc_row[0])) / 60)
                _reason = (
                    f"{candidate['direction']} level {candidate['broken_level']:.0f} "
                    f"last fired {_mins_ago}min ago — cooldown {_LEVEL_COOLDOWN // 60}min"
                )
                if not velocity:
                    log_entry.update({"result": "level_cooldown", "suppressed_reason": _reason})
                    bdb.log_analysis(log_entry)
                _log.debug("[BO-Engine] %s skipped (%s): %s", trigger_tag, "level_cooldown", _reason)
                return
        except Exception as _lc_exc:
            _log.debug("[BO-Engine] level_cooldown check failed: %s", _lc_exc)

        # Consecutive-loss direction cooldown — if _CONSEC_LOSS_LIMIT or more recent
        # losses in this direction within _CONSEC_LOSS_WINDOW, suppress the direction.
        try:
            _cl_cutoff = time.time() - _CONSEC_LOSS_WINDOW
            with bdb._conn() as _cl_conn:
                _cl_rows = _cl_conn.execute(
                    "SELECT outcome FROM bo_signals "
                    "WHERE direction=? AND close_time>? AND outcome IS NOT NULL "
                    "  AND outcome NOT IN ('open','pending') "
                    "ORDER BY close_time DESC LIMIT ?",
                    (candidate["direction"], _cl_cutoff, _CONSEC_LOSS_LIMIT),
                ).fetchall()
            _cl_outcomes = [r[0] for r in _cl_rows]
            if (
                len(_cl_outcomes) >= _CONSEC_LOSS_LIMIT
                and all(o == "loss" for o in _cl_outcomes)
            ):
                _cl_reason = (
                    f"{_CONSEC_LOSS_LIMIT} consecutive {candidate['direction']} losses "
                    f"in last {_CONSEC_LOSS_WINDOW // 3600}h — direction cooldown"
                )
                if not velocity:
                    log_entry.update({"result": "consec_loss_cooldown", "suppressed_reason": _cl_reason})
                    bdb.log_analysis(log_entry)
                _log.info("[BO-Engine] %s suppressed: %s", trigger_tag, _cl_reason)
                return
        except Exception as _cl_exc:
            _log.debug("[BO-Engine] consec_loss check failed: %s", _cl_exc)

        # Cross-engine conflict suppression — if another engine has an active signal
        # in the OPPOSITE direction on the signal bus, hold this signal.
        # window_seconds must not be shorter than realistic trade hold times —
        # a 180s (3min) window made genuinely still-open signals invisible once
        # they outlived it (measured medians: breakout 5.3min, bounce 8.4min),
        # letting this engine open straight into an opposing live position from
        # another engine. is_still_open (flipped by close_bus_entry the instant a
        # trade closes) is the correct authoritative signal; this window is now
        # just a crash/orphan safety net, not an active constraint.
        try:
            from forex_trader.core import database as _cdb
            if _cdb.has_conflict_on_bus("breakout", candidate["direction"], window_seconds=21600.0):
                _conf_reason = (
                    f"Cross-engine conflict: another engine has active "
                    f"{'SELL' if candidate['direction']=='BUY' else 'BUY'} signal"
                )
                if not velocity:
                    log_entry.update({"result": "cross_engine_conflict", "suppressed_reason": _conf_reason})
                    bdb.log_analysis(log_entry)
                _log.info("[BO-Engine] %s suppressed: %s", trigger_tag, _conf_reason)
                return
        except Exception as _cf_exc:
            _log.debug("[BO-Engine] conflict check failed: %s", _cf_exc)

        risk = calculate_breakout_risk_levels(candidate, current_price, atr, adx)
        if not risk:
            log_entry.update({
                "result": "risk_calc_failed",
                "suppressed_reason": "Risk/R:R below minimum — skipped",
            })
            if not velocity:
                bdb.log_analysis(log_entry)
            return

        open_sigs = bdb.get_open_signals()
        same_dir  = [s for s in open_sigs if s.get("direction") == candidate["direction"]]
        if same_dir:
            if not velocity:
                log_entry.update({
                    "result": "duplicate_direction",
                    "suppressed_reason": f"Already have open {candidate['direction']} signal",
                })
                bdb.log_analysis(log_entry)
            return

        try:
            from forex_trader.core.database import get_risk_settings as _grs_claude
            _bo_claude_on = bool(_grs_claude().get("bo_claude_eval_enabled", 1))
        except Exception:
            _bo_claude_on = True

        if _bo_claude_on:
            review = await review_signal(candidate, risk, context)
            _log.info(
                "[BO-Engine] Claude (%s): approved=%s score=%.2f %s",
                trigger_tag, review["approved"], review["score"], review["rationale"][:80],
            )
        else:
            review = {"approved": True, "score": 0.70, "rationale": "Claude eval disabled — ML+rules passed", "fallback": False}
            _log.info("[BO-Engine] Claude eval OFF (%s) — auto-approved", trigger_tag)

        if not review["approved"]:
            # Bootstrap mode: while ML lacks enough training data, override Claude
            # rejections (not errors) so the engine accumulates real-outcome examples.
            ml_info       = bo_ml.summary()
            in_bootstrap  = ml_info.get("labeled_count", 0) < _BOOTSTRAP_SAMPLES
            if in_bootstrap and not review["fallback"]:
                _log.info(
                    "[BO-Engine] Bootstrap override: Claude rejected but only %d/%d samples — "
                    "accepting to build training data",
                    ml_info.get("labeled_count", 0), _BOOTSTRAP_SAMPLES,
                )
                review = dict(review, approved=True, rationale=(
                    f"[bootstrap] {review['rationale']}"
                ))
            else:
                log_entry.update({
                    "result": "claude_rejected",
                    "claude_decision": review["rationale"],
                    "suppressed_reason": (
                        f"Claude rejected ({trigger_tag}): {review['rationale']}"
                        if not review["fallback"]
                        else "Claude error — signal skipped."
                    ),
                    "session":  context.get("session"),
                    "htf_bias": context.get("htf_bias"),
                    "h4_bias":  context.get("h4_bias"),
                    "price":    current_price,
                    "atr_m15":  atr,
                    "adx":      round(adx, 1),
                    "candidate": candidate,
                })
                bdb.log_analysis(log_entry)
                return

        ref_hash   = hashlib.sha256(
            f"{time.time()}{candidate['direction']}{risk['entry_mid']}".encode()
        ).hexdigest()[:8].upper()
        signal_ref = f"BO-{ref_hash}"

        try:
            from forex_trader.core.database import get_risk_settings as _grs
            _bo_strategy = _grs().get("trade_strategy", "conservative")
        except Exception:
            _bo_strategy = "conservative"

        sig_data = {
            "created_at":        time.time(),
            "signal_ref":        signal_ref,
            "direction":         candidate["direction"],
            "breakout_type":     candidate["breakout_type"],
            "broken_level":      candidate["broken_level"],
            "broken_level_type": candidate.get("broken_level_type"),
            "session":           context.get("session"),
            "htf_bias":          context.get("htf_bias"),
            "h4_bias":           context.get("h4_bias"),
            "adx_at_signal":     round(adx, 1),
            "macd_hist":         round(context.get("macd_hist", 0), 4),
            "atr_m15":           round(atr, 2),
            "quality_score":     review["score"],
            "rationale":         review["rationale"],
            "lot_size":          _LOT_SIZE,
            "claude_fallback":   review["fallback"],
            "strategy":          _bo_strategy,
            **risk,
        }
        sig_id = bdb.create_signal(sig_data)

        # Fetch macro context (DXY/GVZ/TIP) for ML features — non-blocking, fails gracefully
        try:
            from forex_trader.test_signal.market_context import get_context as _get_ctx
            _market_ctx = _get_ctx()
        except Exception:
            _market_ctx = {}

        # Inject new contextual ML features directly into sig_data so extract_features
        # can store them alongside the signal and use them at retrain time.
        try:
            from forex_trader.core.news_calendar import get_news_proximity_norm as _get_news
            sig_data["news_proximity_norm"] = _get_news()
        except Exception:
            sig_data["news_proximity_norm"] = 1.0

        try:
            from forex_trader.core import database as _cdb
            sig_data["regime_score"]          = _cdb.get_regime_score(adx, atr)
            sig_data["equity_drawdown_pct"]   = _cdb.get_equity_drawdown_pct()
            sig_data["concurrent_agreement"]  = _cdb.get_concurrent_agreement(
                "breakout", candidate["direction"]
            )
        except Exception:
            sig_data.setdefault("regime_score", 0.5)
            sig_data.setdefault("equity_drawdown_pct", 0.0)
            sig_data.setdefault("concurrent_agreement", 0.0)

        # Write this signal to the shared bus so other engines can see it.
        # ttl_seconds is a crash/orphan safety net only — real closure is
        # signalled by close_bus_entry() (called from _close_and_learn), so the
        # TTL must comfortably outlive any realistic trade hold time or it
        # expires the entry (and stops protecting against conflicts) while the
        # trade is still genuinely open.
        try:
            from forex_trader.core import database as _cdb
            _ml_conf = float(sig_data.get("quality_score") or 0.5)
            _cdb.write_signal_bus("breakout", candidate["direction"], confidence=_ml_conf,
                                   signal_id=sig_id, ttl_seconds=21600.0)
        except Exception:
            pass

        # ML feature extraction + prediction
        ml_features = bo_ml.extract_features(sig_data, market_ctx=_market_ctx)
        if ml_features and sig_id:
            bdb.store_ml_features(sig_id, ml_features)
            ml_pred = bo_ml.predict(ml_features)
            if ml_pred is not None:
                bdb.store_ml_prob(sig_id, ml_pred)
                log_entry["ml_prob"] = round(ml_pred, 4)
                _log.debug("[BO-Engine] ML predicted R=%.3f", ml_pred)

        log_entry.update({
            "result":         f"signal_created:{signal_ref}",
            "claude_decision": review["rationale"],
            "session":         context.get("session"),
            "htf_bias":        context.get("htf_bias"),
            "h4_bias":         context.get("h4_bias"),
            "price":           current_price,
            "atr_m15":         atr,
            "adx":             round(adx, 1),
            "candidate":       candidate,
        })
        bdb.log_analysis(log_entry)

        _log.info(
            "[BO-Engine] SIGNAL %s (%s): %s %s @ $%.2f | SL $%.2f | TP1 $%.2f | "
            "ADX %.1f | %s",
            signal_ref, trigger_tag,
            candidate["direction"], candidate["breakout_type"],
            risk["entry_mid"], risk["stop_loss"], risk["tp1"], adx,
            review["rationale"][:60],
        )
        self.status_detail = f"{signal_ref} via {trigger_tag}"
        self._notify_refresh()

    # ── Outcome monitoring (every 5s) ─────────────────────────────────────────

    async def _outcome_loop(self) -> None:
        while self.is_running:
            try:
                await self._check_outcomes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _log.debug("[BO-Engine] Outcome error: %s", e)
            await asyncio.sleep(_OUTCOME_INTERVAL)

    def _compute_cost_pts(self, spread_raw: float) -> float:
        """Round-trip trade cost in price units (same scale as pnl_pts)."""
        try:
            from forex_trader.core import database as cdb
            fs = cdb.get_fee_settings()
            slippage_pts = fs.get("estimated_slippage_points", 5.0) * 0.01
            commission_rt = (
                fs.get("commission_per_lot_per_side", 0.0) * 2
                + fs.get("commission_round_turn_per_lot", 0.0)
            )
            commission_pts = commission_rt / 100.0
            return round(spread_raw + slippage_pts + commission_pts, 4)
        except Exception:
            return 0.35  # conservative fallback (0.30 spread + 0.05 slippage)

    def _close_and_learn(
        self,
        sig_id: int,
        close_price: float,
        outcome: str,
        note: str,
        entry: float,
        direction: str,
        lot: float,
        cost_pts: float,
    ) -> None:
        """Close a signal, compute net P&L, record ML outcome, trigger batch analysis."""
        sig             = bdb.get_signal_by_id(sig_id)
        remaining_frac  = float(sig.get("remaining_frac") if sig and sig.get("remaining_frac") is not None else 1.0)
        partial_booked  = float(sig.get("partial_pnl_dollars") or 0.0) if sig else 0.0

        raw_pts  = (close_price - entry) if direction == "BUY" else (entry - close_price)
        pnl_pts  = round(raw_pts, 2)
        # Final leg only covers whatever fraction of the position is still open —
        # the rest was already banked via book_partial_close at TP1/TP2.
        leg_net_pts  = round(pnl_pts - cost_pts, 4)
        leg_net_dol  = round(leg_net_pts * lot * remaining_frac * 100.0, 2)
        net_dol      = round(partial_booked + leg_net_dol, 2)
        net_pts      = round(net_dol / (lot * 100.0), 4) if lot else 0.0

        # Re-classify outcome for ML using the TOTAL realized result (partials +
        # final leg) — a trade that banked a TP1 partial before reverting to its
        # break-even-trailed stop is a real win, not a loss, even though the final
        # leg closed flat.
        ml_outcome = outcome
        if net_dol > 0.5:
            ml_outcome = "win"
        elif net_dol < -0.5:
            ml_outcome = "loss"
        else:
            ml_outcome = "be"

        bdb.close_signal(
            sig_id, close_price, ml_outcome, note,
            net_pnl_pts=net_pts, net_pnl_dollars=net_dol,
        )

        try:
            from forex_trader.sync.ledger import push_trade_closed
            push_trade_closed({
                "trade_id":    sig.get("signal_ref") or str(sig_id),
                "engine":      "breakout",
                "direction":   direction,
                "strategy":    sig.get("strategy", "") if sig else "",
                "open_time":   sig.get("created_at") if sig else None,
                "close_time":  time.time(),
                "pnl_dollars": net_dol,
                "outcome":     ml_outcome,
                "tg_source":   "Breakout Engine",
                "mt5_ticket":  sig.get("mt5_ticket") if sig else None,
            })
        except Exception as _le:
            _log.debug("[Ledger] push failed: %s", _le)

        # If live execution was used, try to resolve the actual MT5 P&L immediately.
        # The conservative strategy manages SL/TP independently of the virtual
        # simulation so its final profit may differ; prefer the real figure.
        mt5_ticket = sig.get("mt5_ticket") if sig else None
        if mt5_ticket:
            try:
                from forex_trader.core import database as _mdb
                with _mdb.db() as _mc:
                    _mr = _mc.execute(
                        "SELECT mt5_profit FROM vantage_simulated_trades"
                        " WHERE mt5_ticket=? AND status='closed'",
                        (mt5_ticket,),
                    ).fetchone()
                if _mr and _mr[0] is not None:
                    actual_profit = float(_mr[0])
                    ml_outcome = (
                        "win"  if actual_profit > 1.0  else
                        "loss" if actual_profit < -1.0 else
                        "be"
                    )
                    bdb.update_signal_pnl_from_mt5(sig_id, actual_profit, ml_outcome)
                    _log.debug(
                        "[BO-Engine] signal %d resolved to MT5 profit $%.2f (%s)",
                        sig_id, actual_profit, ml_outcome,
                    )
            except Exception as _e:
                _log.debug("[BO-Engine] MT5 P&L lookup failed for sig %d: %s", sig_id, _e)

        bo_ml.record_outcome(sig_id, ml_outcome)

        try:
            from forex_trader.core import database as _cdb_bus
            _cdb_bus.close_bus_entry("breakout", sig_id)
        except Exception:
            pass

        self._closed_count += 1
        if self._closed_count % _BATCH_REVIEW_EVERY == 0:
            asyncio.ensure_future(self._run_batch_analysis())

    async def _check_outcomes(self) -> None:
        open_sigs = bdb.get_open_signals()
        if not open_sigs:
            return

        tick = await self._bridge.get_tick()
        if not tick:
            return

        bid = float(tick.bid)
        ask = float(tick.ask)
        now = time.time()
        spread_raw = ask - bid
        cost_pts   = self._compute_cost_pts(spread_raw)

        for sig in open_sigs:
            sig_id    = sig["id"]
            direction = sig["direction"]
            status    = sig.get("status", "pending")
            entry     = float(sig.get("entry_mid", 0) or 0)
            lot       = float(sig.get("lot_size") or _LOT_SIZE)
            sl        = float(sig.get("stop_loss", 0) or 0)
            tp1       = float(sig.get("tp1", 0) or 0)
            tp2       = float(sig.get("tp2", 0) or 0)
            tp3       = float(sig.get("tp3", 0) or 0)
            created   = float(sig.get("created_at", 0) or 0)
            sl_moved  = bool(sig.get("sl_moved_to_be", 0))

            # ── Live-execution closure sync ───────────────────────────────────
            # For signals that placed a real MT5 trade, the main engine manages
            # the actual SL/TP (conservative strategy uses its own fixed levels).
            # Read the closure from the main DB instead of relying solely on
            # virtual price checks, which can get stuck when sl_moved_to_be=1
            # and price exits between TP1 and TP2.
            if status == "triggered" and sig.get("mt5_ticket") and sig.get("live_exec_status") == "success":
                try:
                    from forex_trader.core import database as _mdb

                    def _fetch_mt5_close():
                        import sqlite3 as _sl3
                        with _sl3.connect(f"file:{_mdb._DB_PATH}?mode=ro", uri=True) as _mc:
                            _mc.row_factory = _sl3.Row
                            return _mc.execute(
                                "SELECT status, mt5_profit, net_pnl, sl_moved_to_be "
                                "FROM vantage_simulated_trades WHERE mt5_ticket=? AND status='closed'",
                                (sig["mt5_ticket"],),
                            ).fetchone()

                    # Offloaded — see _reconcile_live_pnl for why.
                    _mrow = await _mdb.to_db_thread(_fetch_mt5_close)
                    if _mrow:
                        _profit = float(_mrow["mt5_profit"] or _mrow["net_pnl"] or 0)
                        _mt5_outcome = (
                            "win"  if _profit > 1.0  else
                            "loss" if _profit < -1.0 else
                            "be"
                        )
                        # Derive a close price: use current eval_price as approximation
                        # (actual P&L from MT5 is what matters for learning, not price)
                        _eval_close = bid if direction == "BUY" else ask
                        _log.info(
                            "[BO-Engine] %s closed via MT5 sync: profit=%.2f → %s",
                            sig.get("signal_ref"), _profit, _mt5_outcome,
                        )
                        self._close_and_learn(
                            sig_id, _eval_close, _mt5_outcome,
                            f"MT5 closed (mt5_profit={_profit:.2f})",
                            entry, direction, lot, cost_pts,
                        )
                        self._notify_refresh()
                        continue
                except Exception as _sync_exc:
                    _log.debug("[BO-Engine] MT5 closure sync failed for %s: %s", sig.get("signal_ref"), _sync_exc)

            # Expire stale signals
            if created and (now - created) > _MAX_SIGNAL_AGE:
                bdb.expire_signal(sig_id, f"Expired after {_MAX_SIGNAL_AGE / 3600:.0f}h")
                _log.info("[BO-Engine] %s expired", sig.get("signal_ref"))
                self._notify_refresh()
                continue

            # Live-executed signals must only be closed via the MT5 sync above.
            # Skipping virtual SL/TP here ensures the balance reflects the real
            # MT5 profit rather than a fabricated price at evaluation time.
            if status == "triggered" and sig.get("mt5_ticket") and sig.get("live_exec_status") == "success":
                continue

            # Auto-trigger pending (breakouts are market-entry at signal time)
            if status == "pending":
                from forex_trader.core.database import is_session_allowed as _isa
                _sess_ok, _sess_name = _isa()
                if not _sess_ok:
                    _log.debug(
                        "[BO-Engine] %s held: session '%s' not enabled in Trading Markets",
                        sig.get("signal_ref"), _sess_name,
                    )
                    continue
                price_exec = ask if direction == "BUY" else bid
                bdb.trigger_signal(sig_id, price_exec)
                _log.info("[BO-Engine] %s triggered @ %.2f", sig.get("signal_ref"), price_exec)
                status = "triggered"
                # Live execution — place real MT5 trade if bo_live_execution is ON
                await self._execute_live(sig, price_exec, tick)

            if status != "triggered":
                continue

            # Orphan watchdog: live execution was on at trigger time but
            # live_exec_status was never written (crash/restart mid-execute).
            trigger_time = float(sig.get("trigger_time") or 0)
            if (trigger_time > 0
                    and not sig.get("live_exec_status")
                    and (now - trigger_time) > 120):
                bdb.update_live_exec_result(
                    sig_id, None, None, "failed:orphaned_no_response"
                )
                _log.warning(
                    "[BO-Engine] %s triggered %ds ago but live_exec_status never "
                    "written — marking orphaned",
                    sig.get("signal_ref"), int(now - trigger_time),
                )

            eval_price = bid if direction == "BUY" else ask

            # ── Time stop ─────────────────────────────────────────────────────
            # 2026-07-16 rebuild: winners averaged 14.9min to resolve vs 9.2min
            # for losses, so the old "not ≥0.5pt in profit after 15min" rule was
            # scratching exactly the slow winners. Now only closes a trade that
            # is demonstrably FAILING — beyond 20% of its stop distance in the
            # red after time_stop_mins (default 30) with no partial banked.
            _tp_trig = float(sig.get("trigger_price") or entry or 0)
            if (_tp_trig > 0 and trigger_time > 0
                    and float(sig.get("remaining_frac") or 1.0) >= 0.999):
                _unreal_bo = round(
                    (eval_price - _tp_trig) if direction == "BUY"
                    else (_tp_trig - eval_price), 2,
                )
                _sl_dist_bo = float(sig.get("sl_dist") or 0) or abs(entry - sl) or 1.0
                _ts_mins_bo = ap.get("time_stop_mins")
                if ((now - trigger_time) > _ts_mins_bo * 60
                        and _unreal_bo < -0.2 * _sl_dist_bo):
                    _ts_outcome = "loss" if _unreal_bo < -1.0 else "be"
                    self._close_and_learn(
                        sig_id, eval_price, _ts_outcome,
                        f"Time stop after {int((now - trigger_time) / 60)}min @ {_unreal_bo:+.1f}pts",
                        entry, direction, lot, cost_pts,
                    )
                    _log.info(
                        "[BO-Engine] %s time stop → %s (%+.1fpts after %dmin)",
                        sig.get("signal_ref"), _ts_outcome.upper(), _unreal_bo,
                        int((now - trigger_time) / 60),
                    )
                    self._notify_refresh()
                    continue

            # SL hit
            sl_hit = (direction == "BUY" and eval_price <= sl) or \
                     (direction == "SELL" and eval_price >= sl)
            if sl_hit:
                outcome = "be" if sl_moved else "loss"
                self._close_and_learn(
                    sig_id, eval_price, outcome, f"SL @ {eval_price:.2f}",
                    entry, direction, lot, cost_pts,
                )
                _log.info("[BO-Engine] %s %s", sig.get("signal_ref"), outcome.upper())
                self._notify_refresh()
                continue

            # TP3 — full winner, close position
            tp3_hit = tp3 and (
                (direction == "BUY"  and eval_price >= tp3) or
                (direction == "SELL" and eval_price <= tp3)
            )
            if tp3_hit:
                self._close_and_learn(
                    sig_id, eval_price, "win", f"TP3 @ {eval_price:.2f}",
                    entry, direction, lot, cost_pts,
                )
                _log.info("[BO-Engine] %s WIN (TP3)", sig.get("signal_ref"))
                self._notify_refresh()
                continue

            # Partial-close scale-out — replaces the old pure trail-the-stop
            # approach. Live data showed avg win ($41) SMALLER than avg loss
            # ($49) despite a 52.6% win rate: trades were spiking through TP1/TP2
            # and reverting through the trailed stop before TP3, giving the whole
            # gain back. Banking real dollars at each tier locks in profit instead
            # of leaving 100% of the position exposed to a full round-trip.
            # remaining_frac gates each tier so it only fires once, using the
            # previous bug's failure mode (checking sl_moved_to_be, which TP1
            # already sets) as the reason TP2 logic never actually ran before.
            remaining_frac = float(
                sig.get("remaining_frac") if sig.get("remaining_frac") is not None else 1.0
            )

            # Scale-out fractions: 33% banked at TP1, 33% at TP2, 34% rides to
            # TP3. The previous 50/25/25 split banked too much too early — live
            # data showed avg win $39 vs avg loss $48 because only a quarter of
            # the position ever reached the levels that pay for the full-size
            # losses. GD Copy (the profitable engine) proves gold rewards
            # letting more size run the ladder.
            _TP1_FRAC = 0.33
            _TP2_FRAC = 0.33

            # TP2 — bank a second partial, trail SL to TP1
            tp2_hit = tp2 and (1.0 - _TP1_FRAC - _TP2_FRAC) < remaining_frac <= (1.0 - _TP1_FRAC) + 1e-6 and (
                (direction == "BUY"  and eval_price >= tp2) or
                (direction == "SELL" and eval_price <= tp2)
            )
            if tp2_hit:
                leg_pts     = (eval_price - entry) if direction == "BUY" else (entry - eval_price)
                leg_net_dol = round((leg_pts - cost_pts) * lot * _TP2_FRAC * 100.0, 2)
                bdb.book_partial_close(sig_id, leg_net_dol, _TP2_FRAC, f"TP2 partial @ {eval_price:.2f}")
                with bdb._conn() as conn:
                    conn.execute(
                        "UPDATE bo_signals SET stop_loss=? WHERE id=?", (tp1, sig_id),
                    )
                _log.info(
                    "[BO-Engine] %s TP2 partial booked $%.2f — SL → TP1 %.2f",
                    sig.get("signal_ref"), leg_net_dol, tp1,
                )
                self._notify_refresh()
                continue

            # TP1 — bank first partial, move SL to break-even PLUS the round-trip
            # cost so a BE exit on the remainder nets $0 rather than -cost (the
            # old raw-entry BE bled the spread on all 12 'be' closes).
            tp1_hit = tp1 and remaining_frac >= 1.0 - 1e-6 and (
                (direction == "BUY"  and eval_price >= tp1) or
                (direction == "SELL" and eval_price <= tp1)
            )
            if tp1_hit:
                leg_pts     = (eval_price - entry) if direction == "BUY" else (entry - eval_price)
                leg_net_dol = round((leg_pts - cost_pts) * lot * _TP1_FRAC * 100.0, 2)
                bdb.book_partial_close(sig_id, leg_net_dol, _TP1_FRAC, f"TP1 partial @ {eval_price:.2f}")
                be_px = round(entry + cost_pts, 2) if direction == "BUY" else round(entry - cost_pts, 2)
                bdb.move_sl_to_be(sig_id, be_price=be_px)
                _log.info(
                    "[BO-Engine] %s TP1 partial booked $%.2f — SL → BE+cost %.2f",
                    sig.get("signal_ref"), leg_net_dol, be_px,
                )
                self._notify_refresh()

    # ── Live MT5 execution ────────────────────────────────────────────────────

    async def _execute_live(self, sig: dict, fill_px: float, tick) -> None:
        """Place a real MT5 trade via the main engine when bo_live_execution is ON."""
        sig_id     = sig.get("id")
        signal_ref = sig.get("signal_ref") or f"BO-{sig_id or 0:04d}"
        direction  = (sig.get("direction") or "").upper()

        if self._main_engine is None:
            _log.warning("[BO-LiveExec] %s skipped — main engine not linked", signal_ref)
            if sig_id:
                bdb.update_live_exec_result(sig_id, None, None, "skipped:no_main_engine")
            return

        from forex_trader.core import database as _cdb
        rs = _cdb.get_risk_settings()
        if not bool(rs.get("bo_live_execution", 0)):
            if sig_id:
                bdb.update_live_exec_result(sig_id, None, None, "skipped:live_off")
            return

        # Toxic-hour blocklist: blocks real money only — the signal above
        # this call still generated and will still track/close/train
        # normally. Trading > Strategy > Risk Settings toggle, shared with
        # the Bounce generator, off by default.
        if bool(rs.get("hour_blocklist_enabled", 0)):
            from datetime import datetime as _dt, timezone as _tz
            from forex_trader.core.regime import BREAKOUT_BLOCKED_HOURS_UTC
            _hour_now = _dt.now(_tz.utc).hour
            if _hour_now in BREAKOUT_BLOCKED_HOURS_UTC:
                reason = f"hour_blocklist: {_hour_now:02d} UTC (measured -$1,079 in 12-14 window)"
                _log.info("[BO-LiveExec] %s skipped — %s", signal_ref, reason)
                if sig_id:
                    bdb.update_live_exec_result(sig_id, None, None, f"skipped:{reason}")
                return

        vantage_sig_id = None
        try:
            base_lot = float(sig.get("lot_size") or 0)
            ml_prob  = sig.get("ml_prob")

            # ML gate: block live execution when model predicts a negative R-multiple.
            # ml_prob now stores the predicted R-multiple (positive = profitable).
            # Gate (and lot-scaling below) require the BATCH model — the online SGD
            # alone is rebuilt from scratch after every feature-version bump and its
            # first few predictions are noise (it blocked a winning trade on
            # predicted R=-0.005 with 4 samples). Rules + quality score still apply.
            _BO_ML_R_FLOOR = 0.0
            if ml_prob is not None and bo_ml.has_batch() and float(ml_prob) < _BO_ML_R_FLOOR:
                reason = f"ML gate: predicted R={float(ml_prob):.3f} < 0 (expected loss)"
                _log.info("[BO-LiveExec] %s %s — %s", signal_ref, direction, reason)
                if sig_id:
                    bdb.update_live_exec_result(sig_id, None, None, f"skipped:{reason}")
                return

            if base_lot > 0 and ml_prob is not None and bo_ml.has_batch():
                # Scale lot by predicted R-multiple: R=1.0→1.0×, R=2.0→1.3×, R=0.1→0.6×
                ml_scale = round(max(0.5, min(1.3, 0.5 + float(ml_prob) * 0.4)), 2)
                base_lot = round(base_lot * ml_scale, 2)

            # Kelly Criterion fractional sizing
            try:
                if bool(rs.get("kelly_sizing_enabled", 0)) and base_lot > 0:
                    _recent = bdb.get_recent_closed_signals(limit=50)
                    _wins   = [s for s in _recent if s.get("outcome") == "win"]
                    _losses = [s for s in _recent if s.get("outcome") == "loss"]
                    _n      = len(_wins) + len(_losses)
                    if _n >= 20 and _wins and _losses:
                        _avg_w = sum(s.get("pnl_pts", 0) or 0 for s in _wins)  / len(_wins)
                        _avg_l = abs(sum(s.get("pnl_pts", 0) or 0 for s in _losses) / len(_losses))
                        if _avg_l > 0 and _avg_w > 0:
                            _wr = len(_wins) / _n
                            _R  = _avg_w / _avg_l
                            _kf = _wr - (1 - _wr) / _R
                            _hk = _kf / 2
                            _km = round(max(0.75, min(1.25, 1.0 + _hk)), 2)
                            base_lot = round(base_lot * _km, 2)
                            _log.info(
                                "[BO-LiveExec] Kelly: wr=%.0f%% R=%.2f f=%.3f mult=%.2f lot→%.2f",
                                _wr * 100, _R, _kf, _km, base_lot,
                            )
            except Exception as _ke:
                _log.debug("[BO-LiveExec] Kelly sizing error: %s", _ke)

            entry = float(sig.get("entry_mid") or fill_px)
            sl    = float(sig.get("stop_loss") or 0)
            tp1   = sig.get("tp1")
            tp2   = sig.get("tp2")
            tp3   = sig.get("tp3")

            main_sig = self._main_engine.create_signal(
                source_name = "Breakout Engine",
                direction   = direction,
                entry_low   = round(entry - 0.5, 2),
                entry_high  = round(entry + 0.5, 2),
                stop_loss   = sl,
                tp1=tp1, tp2=tp2, tp3=tp3,
                lot_size = base_lot,
                notes    = signal_ref,
            )
            vantage_sig_id = main_sig["signal_id"]
            result = await self._main_engine.open_trade_from_signal(vantage_sig_id, tick=tick)
            mt5_ticket = result.get("mt5_ticket")
            _log.info(
                "[BO-LiveExec] %s %s live trade opened: ticket=%s entry=%.2f",
                signal_ref, direction, mt5_ticket, result.get("entry_price", fill_px),
            )
            if sig_id:
                bdb.update_live_exec_result(sig_id, mt5_ticket, vantage_sig_id, "success")
        except Exception as exc:
            reason = str(exc)[:120]
            _log.warning("[BO-LiveExec] %s live trade failed: %s", signal_ref, reason)
            if sig_id:
                bdb.update_live_exec_result(sig_id, None, vantage_sig_id, f"failed:{reason}")

    # ── Batch learning / parameter optimisation ───────────────────────────────

    async def _run_batch_analysis(self) -> None:
        """
        Every _BATCH_REVIEW_EVERY closed trades, ask Claude to review breakout
        signal patterns and recommend adaptive parameter adjustments.
        Mirrors the same mechanism in the bounce engine.
        """
        cfg = cfg_module.load()
        if not ai_provider.is_configured(cfg):
            return

        recent = bdb.get_recent_closed_signals(limit=_BATCH_REVIEW_EVERY)
        if len(recent) < 3:
            return

        stats     = bdb.get_stats()
        by_sess   = bdb.get_perf_by_session()
        by_type   = bdb.get_perf_by_breakout_type()
        by_adx    = bdb.get_perf_by_adx_band()
        by_bias   = bdb.get_perf_by_bias()
        ml_info   = bo_ml.summary()
        balance   = bdb.get_virtual_balance()

        trade_lines = []
        for s in recent:
            ref = s.get("signal_ref") or f"BO-{s['id']:04d}"
            trade_lines.append(
                f"  {ref} {s.get('direction')} {s.get('breakout_type','?'):8s} "
                f"{(s.get('outcome') or '?').upper():6s}  "
                f"pnl={s.get('pnl_pts', 0):+.1f}pts "
                f"net={s.get('net_pnl_pts', 0) or 0:+.1f}pts "
                f"(${s.get('net_pnl_dollars', 0) or 0:+.2f})  "
                f"session={s.get('session')}  bias={s.get('htf_bias')}  "
                f"adx={s.get('adx_at_signal', 0):.0f}  "
                f"quality={s.get('quality_score', 0):.0%}  "
                f"rr={s.get('rr_tp1', 0):.1f}  ml_prob={s.get('ml_prob') or 'n/a'}"
            )

        sess_lines  = [
            f"  {r.get('session')}: {r.get('wins',0)}W/{r.get('losses',0)}L "
            f"total=${r.get('total_pnl',0) or 0:+.2f}"
            for r in by_sess
        ]
        type_lines  = [
            f"  {r.get('breakout_type')}: {r.get('wins',0)}W/{r.get('losses',0)}L "
            f"total=${r.get('total_pnl',0) or 0:+.2f}"
            for r in by_type
        ]
        adx_lines   = [
            f"  {r.get('adx_band')}: {r.get('wins',0)}W/{r.get('losses',0)}L "
            f"avg=${r.get('avg_pnl',0) or 0:+.2f}"
            for r in by_adx
        ]

        ml_str = (
            f"ML: trained={ml_info['trained']} "
            f"labeled={ml_info['labeled_count']}/{ml_info['min_needed']} "
            f"has_batch={ml_info['has_batch']} has_online={ml_info['has_online']}"
        )

        system_prompt = (
            "You are an algorithmic trading parameter optimizer for a XAUUSD BREAKOUT signal generator. "
            "Analyse the provided trade history and respond ONLY with a single minified JSON object — "
            "no other text:\n"
            '{"adjustments":[{"param":"<name>","new_value":<number>,"reason":"<one sentence>"}],'
            '"summary":"<2-3 sentence analysis>"}\n\n'
            "Available parameters you may adjust:\n"
            + ap.catalogue_for_prompt() +
            "\n\nRules:\n"
            "- Only recommend changes supported by clear evidence in the data.\n"
            "- If sample < 5 or win rate ≥ 55%, return empty adjustments.\n"
            "- Never set a value outside the stated range — it will be clamped anyway.\n"
            "- require_dual_bias must be exactly 0 or 1.\n"
            "- Prefer small incremental changes (±0.05 to ±0.15) over large jumps.\n"
            "- For breakouts: higher ADX thresholds reduce false signals but also reduce trades."
        )

        user_prompt = "\n".join([
            f"Virtual account balance: ${balance:.2f} (started $1,000.00)",
            f"Overall: {stats['wins']}W / {stats['losses']}L / {stats['be']}BE  "
            f"win_rate={stats['win_rate']}%  avg_pnl=${stats['avg_pnl_dollars']:+.2f}",
            ml_str,
            "",
            f"Last {len(recent)} trades:",
            *trade_lines,
            "",
            "Performance by session:",
            *sess_lines,
            "",
            "Performance by breakout type (go vs retest):",
            *type_lines,
            "",
            "Performance by ADX band:",
            *adx_lines,
        ])

        try:
            import json as _json

            raw = await ai_provider.complete(cfg, system_prompt, user_prompt, max_tokens=400, timeout=25)
            if not raw:
                # Was previously a debug-only log with no DB trace — every failure
                # here (bad JSON, timeout, API error, e.g. an expired/invalid AI
                # key) vanished silently instead of showing up as "learned
                # parameters never change." Confirmed live: bo_analysis_log had
                # zero batch_analysis entries across 269 closed trades (~26
                # expected runs), while the mirrored fix in test_signal/engine.py
                # (see its comment there) was already catching and logging this
                # exact failure mode for the Bounce engine.
                _log.warning("[BO-Engine] Batch analysis: empty response from AI")
                bdb.log_analysis({
                    "ts":              time.time(),
                    "result":          "batch_analysis_failed",
                    "claude_decision": f"Batch analysis failed ({len(recent)} trades): empty response from AI",
                })
                return
            data = _json.loads(raw)

            adjustments = data.get("adjustments", [])
            applied     = []
            for adj in adjustments:
                param  = adj.get("param", "")
                value  = adj.get("new_value")
                reason = adj.get("reason", "")
                if param and value is not None:
                    new_v = ap.apply_adjustment(param, float(value), reason)
                    if new_v is not None:
                        applied.append(f"{param}→{new_v:.4g}")

            applied_str = (", ".join(applied)) if applied else "no changes"
            summary     = data.get("summary", "")
            _log.info(
                "[BO-Engine] Batch analysis (%d trades): %s. %s",
                len(recent), applied_str, summary[:120],
            )
            bdb.log_analysis({
                "ts":              time.time(),
                "result":          f"batch_analysis:{len(recent)}_trades",
                "claude_decision": f"Batch ({len(recent)} trades): {applied_str}. {summary}",
            })

        except Exception as e:
            # Log failures too (not just successes) — mirrors the same fix in
            # test_signal/engine.py's _run_batch_analysis, ported here since this
            # engine had the original silent-swallow behavior that fix addressed.
            err_msg = f"Batch analysis failed ({len(recent)} trades): {e}"
            _log.warning("[BO-Engine] %s", err_msg)
            bdb.log_analysis({
                "ts":              time.time(),
                "result":          "batch_analysis_failed",
                "claude_decision": err_msg,
            })
