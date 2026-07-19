"""
TestSignalEngine — runs in the background, generates XAUUSD signals in test mode.

Guarantees:
  - Never places any MT5 orders (read-only bridge access)
  - Never sends Telegram messages
  - All output goes to the test database and test_signal.log only
  - Completely isolated from the main SimulationEngine

Virtual trading model (XAUUSD):
  - Starting balance: $1,000
  - Leverage: 1:500 (Vantage Markets)
  - Lot size: fixed 0.1 lots per trade
  - At 0.1 lot: 1 price-unit move = $10 P&L
  - Strategy mirrors the active strategy set in the main app
"""
from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import forex_trader.config as cfg_module
from forex_trader.core import ai_provider
from forex_trader.core.dpm_engine import compute_atr

from forex_trader.test_signal import database as tdb
from forex_trader.test_signal import adaptive_params as ap
from forex_trader.test_signal.signal_generator import (
    compute_htf_bias,
    compute_h4_bias,
    compute_adx,
    compute_macd_hist,
    detect_regime,
    identify_key_levels,
    check_entry_trigger,
    check_scalp_trigger,
    calculate_risk_levels,
    calculate_scalp_risk_levels,
    get_session,
    session_quality,
    is_news_window,
)
from forex_trader.test_signal.claude_reviewer import review_signal
from forex_trader.test_signal import ml_engine as ml
from forex_trader.test_signal import market_context as mktctx

if TYPE_CHECKING:
    from forex_trader.core.mt5_bridge import MT5BridgeClient

# ── Dedicated logger ──────────────────────────────────────────────────────────
_log = logging.getLogger("test_signal")

_LOG_SETUP_DONE = False


def _fetch_recent_tg_signals(max_age_seconds: int = 7200) -> list[dict]:
    """Return up to 3 Telegram signals from the main DB received in the last max_age_seconds."""
    import time as _t
    try:
        from forex_trader.core import database as _main_db
        cutoff = _t.time() - max_age_seconds
        with _main_db.db() as conn:
            rows = conn.execute(
                "SELECT source_name, direction, entry_low, entry_high, stop_loss, "
                "tp1, tp2, tp3, created_at FROM vantage_signals "
                "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 3",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        _log.debug("[TestSignal] TG signal fetch error: %s", e)
        return []


def _fetch_tg_outcomes(max_age_days: int = 7) -> list[dict]:
    """
    Return TG signal rows with a success flag from the main DB.
    Success = signal's trade reached TP1 (partial close with reason LIKE 'TP1%').
    """
    import time as _t
    try:
        from forex_trader.core import database as _main_db
        cutoff = _t.time() - max_age_days * 86400
        with _main_db.db() as conn:
            rows = conn.execute(
                """SELECT vs.source_name, vs.direction,
                          CASE WHEN tp1_hit.trade_id IS NOT NULL THEN 1 ELSE 0 END as success
                   FROM vantage_signals vs
                   LEFT JOIN vantage_simulated_trades vst ON vst.signal_id = vs.signal_id
                   LEFT JOIN (
                       SELECT DISTINCT trade_id FROM vantage_partial_closes
                       WHERE reason LIKE 'TP1%' AND lots_closed > 0
                   ) tp1_hit ON tp1_hit.trade_id = vst.trade_id
                   WHERE vs.created_at >= ?
                   ORDER BY vs.created_at DESC LIMIT 100""",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        _log.debug("[TestSignal] TG outcome fetch error: %s", e)
        return []


def _setup_log(data_dir: Path) -> None:
    global _LOG_SETUP_DONE
    if _LOG_SETUP_DONE:
        return
    log_path = data_dir / "test_signal.log"
    fh = logging.handlers.TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=14, encoding="utf-8", utc=False,
    )
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s — %(message)s"))
    fh.setLevel(logging.DEBUG)
    _log.setLevel(logging.DEBUG)
    _log.addHandler(fh)
    _log.propagate = False
    _LOG_SETUP_DONE = True


# ── Constants ─────────────────────────────────────────────────────────────────

_CYCLE_INTERVAL         = 60     # seconds between scheduled analysis cycles (1 min)
_OUTCOME_INTERVAL       = 5      # seconds between outcome checks (was 60 — scalp requires fast polling)
_SIGNAL_MAX_AGE_H       = 2 / 60  # 2 minutes — matches main engine; scalping signals not zone-filled in 2 min are stale
_MIN_ZONE_DWELL         = 2      # consecutive 5s checks price must be inside zone before trigger
                                  # (filters spike entries; 2 × 5s = 10s min dwell)
_RISK_PCT               = 0.01   # fallback risk % (1% of balance) — mirrors main app default
_LEVERAGE               = 500    # Vantage Markets 1:500 leverage
_MIN_LOT                = 0.01   # minimum virtual lot size
_FIXED_LOT              = 0.10   # fixed lot size — 0.1 lots at 1:500 leverage
_BATCH_REVIEW_EVERY     = 10     # run batch learning analysis every N closed trades

# ML gate and risk controls
_TS_ML_R_FLOOR      = 0.0    # block signals with predicted R-multiple below this
_CONSEC_LOSS_LIMIT  = 3      # consecutive losses before direction cooldown
_CONSEC_LOSS_WINDOW = 7200   # lookback window for consecutive-loss check (seconds)

# Fast monitoring (velocity loop)
_VELOCITY_INTERVAL      = 3      # seconds between price samples
_VELOCITY_WINDOW        = 20     # seconds over which velocity is measured
_VELOCITY_THRESHOLD     = 10.0   # pts in window before emergency scan fires
_SWEEP_REVERSAL_PT      = 3.0    # pts reversal after a swing-level touch to confirm sweep
_SWEEP_TIMEOUT          = 30     # seconds before a pending sweep expires
_EMERGENCY_SCAN_COOLDOWN = 120   # minimum seconds between consecutive emergency scans
_CANDLE_REFRESH_INTERVAL = 30.0  # seconds between background candle cache refreshes
_CANDLE_CACHE_MAX_AGE    = 25.0  # max cache age (s) to use cached candles on emergency scan


def _calc_lot_size(
    balance: float,
    sl_dist: float,
    risk_pct: float = _RISK_PCT,
    fixed_lot: float = 0.0,
) -> tuple[float, float]:
    """
    Returns (lot_size, risk_amount) for a XAUUSD virtual trade.

    Priority:
      1. fixed_lot > 0  — use it directly (mirrors main app strategy_lot_size).
      2. Otherwise      — risk-based sizing: risk_pct % of balance / (sl_dist × $100/lot/pt).

    Leverage (1:500) lowers the margin requirement per lot but does NOT change
    the risk-based lot calculation — it just means larger positions are feasible
    without posting the full notional as margin.  When fixed_lot is read from
    the main app (which already accounts for leverage in practice), the two
    accounts stay in sync automatically.
    """
    if fixed_lot > 0:
        risk_amount = round(fixed_lot * sl_dist * 100.0, 2)
        return fixed_lot, risk_amount
    risk_amount = round(balance * risk_pct, 2)
    if sl_dist <= 0:
        return _MIN_LOT, risk_amount
    raw = risk_amount / (sl_dist * 100.0)
    lot_size = max(_MIN_LOT, math.floor(raw * 100) / 100)
    return lot_size, risk_amount


def _calc_pnl_dollars(pnl_pts: float, lot_size: float) -> float:
    return round(pnl_pts * lot_size * 100.0, 2)


def _compute_cost_pts(spread_raw: float = 0.30) -> float:
    """
    Estimated round-trip trade cost in price units (same scale as pnl_pts).
    Covers: spread + slippage + commission.
    `spread_raw` = tick.ask - tick.bid at the time of close.
    """
    try:
        from forex_trader.core import database as cdb
        fs = cdb.get_fee_settings()
        slippage_pts = fs.get("estimated_slippage_points", 5.0) * 0.01  # raw MT5 pts → price units
        commission_rt = (
            fs.get("commission_per_lot_per_side", 0.0) * 2
            + fs.get("commission_round_turn_per_lot", 0.0)
        )
        commission_pts = commission_rt / 100.0  # $ per lot → price units
        return round(spread_raw + slippage_pts + commission_pts, 4)
    except Exception:
        return round(spread_raw + 0.05, 4)  # fallback: spread + 0.05 slippage


# ── Engine ────────────────────────────────────────────────────────────────────

def _compute_swing_levels(m15_candles: list) -> tuple[float, float]:
    """Return (swing_high, swing_low) from the last 20 M15 bars."""
    if len(m15_candles) < 5:
        return 0.0, 0.0
    recent = m15_candles[-20:]
    highs = [float(c.get("high", 0) or 0) for c in recent]
    lows  = [float(c.get("low",  0) or 0) for c in recent]
    return max(highs), min(l for l in lows if l > 0)


class TestSignalEngine:
    def __init__(self, bridge: "MT5BridgeClient"):
        self._bridge        = bridge
        self._running       = False
        self._cycle_task:    Optional[asyncio.Task] = None
        self._outcome_task:  Optional[asyncio.Task] = None
        self._velocity_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._last_m15_candle_time: float = 0.0
        self._last_m5_candle_time:  float = 0.0
        self._last_cycle_at:         float = 0.0
        self._status: str = "stopped"
        self._status_detail: str = ""
        self._closed_trade_count: int = 0
        self._refresh_callbacks: list = []
        # Main engine reference (set by app.py) — used for live execution
        self._main_engine = None
        # Zone dwell tracking: {signal_id: consecutive_in_zone_count}
        # A pending signal only triggers once it has been inside the entry zone
        # for _MIN_ZONE_DWELL consecutive outcome-check cycles (_OUTCOME_INTERVAL s each).
        self._zone_dwell: dict[int, int] = {}
        # Fast monitoring state
        self._force_scan:          bool  = False
        self._force_scan_event:    Optional[asyncio.Event] = None  # created in start()
        self._last_emergency_scan: float = 0.0
        self._cached_swing_high:   float = 0.0
        self._cached_swing_low:    float = 0.0
        self._sweep_touch_high:    float = 0.0
        self._sweep_touch_low:     float = 0.0
        self._sweep_touch_time:    float = 0.0
        # Candle cache — populated by velocity loop, used by emergency scans
        self._cached_candles:      dict  = {}   # {tf: (timestamp, candles_list)}
        self._last_candle_refresh: float = 0.0

    # ── Live P&L reconciliation ───────────────────────────────────────────────

    async def _reconcile_live_pnl(self) -> None:
        """Sync closed test_signal P&L with actual MT5 profit where they diverge."""
        try:
            from forex_trader.core import database as _mdb

            def _do_reconcile() -> int:
                import sqlite3 as _sqlite3
                with tdb._conn() as conn:
                    rows = conn.execute(
                        "SELECT id, mt5_ticket, pnl_dollars, outcome FROM test_signals"
                        " WHERE status='closed' AND mt5_ticket IS NOT NULL"
                    ).fetchall()
                if not rows:
                    return 0
                _db_path = _mdb._DB_PATH  # type: ignore[attr-defined]
                main_conn = _sqlite3.connect(f"file:{_db_path}?mode=ro", uri=True)
                main_conn.row_factory = _sqlite3.Row
                updated = 0
                try:
                    for row in rows:
                        sig_id, ticket, sim_pnl, sim_outcome = (
                            row[0], row[1], row[2] or 0.0, row[3] or ""
                        )
                        cur = main_conn.execute(
                            "SELECT mt5_profit FROM vantage_simulated_trades"
                            " WHERE mt5_ticket=? AND status='closed'",
                            (ticket,),
                        )
                        main_row = cur.fetchone()
                        if not main_row:
                            continue
                        actual_profit = float(main_row["mt5_profit"] or 0.0)
                        if abs(actual_profit - float(sim_pnl)) < 0.01:
                            continue
                        mt5_outcome = (
                            "win"  if actual_profit > 1.0  else
                            "loss" if actual_profit < -1.0 else
                            "be"
                        )
                        tdb.update_signal_pnl_from_mt5(sig_id, actual_profit, mt5_outcome)
                        if sim_outcome != mt5_outcome:
                            ml.record_outcome(sig_id, mt5_outcome)
                        updated += 1
                        _log.info(
                            "[TestSignal] Reconciled SIG-%04d (ticket %s): sim=$%.2f → MT5=$%.2f (%s)",
                            sig_id, ticket, sim_pnl, actual_profit, mt5_outcome,
                        )
                finally:
                    main_conn.close()
                return updated

            # Offloaded to the DB worker thread — this used to open a raw
            # sqlite3.connect() directly on the event loop thread, which
            # blocks the ENTIRE app (not just this task) for as long as the
            # main DB is lock-contended. Confirmed live: stalls up to 43s
            # traced to this exact pattern (repeated across all three sub-
            # engines) under normal write load from the main engine.
            updated = await _mdb.to_db_thread(_do_reconcile)
            if updated:
                _log.info("[TestSignal] Reconciled %d live P&L records with MT5 actuals", updated)
        except Exception as exc:
            _log.warning("[TestSignal] P&L reconciliation failed: %s", exc)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            # Self-heal: recreate any tasks that exited while the engine was
            # supposed to be running (e.g. unhandled exception that bypassed
            # the loop's except clause, or external cancellation).
            healed = False
            if self._cycle_task is None or self._cycle_task.done():
                self._cycle_task = asyncio.create_task(self._cycle_loop())
                _log.warning("TestSignalEngine: cycle task was dead — restarted")
                healed = True
            if self._outcome_task is None or self._outcome_task.done():
                self._outcome_task = asyncio.create_task(self._outcome_loop())
                _log.warning("TestSignalEngine: outcome task was dead — restarted")
                healed = True
            if healed:
                self._status = "running"
            return
        self._running = True
        self._status  = "running"
        self._force_scan_event = asyncio.Event()
        # Restore closed-trade count from DB so batch-learning fires correctly
        # even after a restart (counter resets to 0 otherwise).
        try:
            self._closed_trade_count = tdb.get_stats().get("closed", 0)
        except Exception:
            pass
        self._cycle_task    = asyncio.create_task(self._cycle_loop())
        self._outcome_task  = asyncio.create_task(self._outcome_loop())
        self._velocity_task = asyncio.create_task(self._velocity_loop())
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        asyncio.create_task(self._reconcile_live_pnl())
        _log.info("TestSignalEngine started (closed_trade_count=%d)", self._closed_trade_count)

    def stop(self) -> None:
        self._running = False
        self._status  = "stopped"
        for t in (self._cycle_task, self._outcome_task, self._velocity_task, self._watchdog_task):
            if t and not t.done():
                t.cancel()
        _log.info("TestSignalEngine stopped")

    @property
    def is_running(self) -> bool:
        """True only when the engine is supposed to run AND at least one task is alive."""
        if not self._running:
            return False
        return (
            (self._cycle_task is not None and not self._cycle_task.done())
            or (self._outcome_task is not None and not self._outcome_task.done())
        )

    @property
    def status(self) -> str:
        return self._status

    @property
    def status_detail(self) -> str:
        return self._status_detail

    @property
    def last_cycle_at(self) -> float:
        return self._last_cycle_at

    def set_main_engine(self, engine) -> None:
        self._main_engine = engine

    def add_refresh_callback(self, cb) -> None:
        self._refresh_callbacks = [cb]

    def _notify_refresh(self) -> None:
        for cb in self._refresh_callbacks:
            try:
                cb()
            except Exception:
                pass

    # ── Watchdog ──────────────────────────────────────────────────────────────

    async def _watchdog_loop(self) -> None:
        """Check every 2 minutes that cycle/outcome tasks are still alive.
        If either exited unexpectedly, restart it without requiring a manual
        stop/start cycle."""
        while self._running:
            await asyncio.sleep(120)
            if not self._running:
                break
            for attr, name, coro_fn in (
                ("_cycle_task",    "cycle",    self._cycle_loop),
                ("_outcome_task",  "outcome",  self._outcome_loop),
                ("_velocity_task", "velocity", self._velocity_loop),
            ):
                task: Optional[asyncio.Task] = getattr(self, attr)
                if task is not None and task.done():
                    exc = None
                    try:
                        exc = task.exception()
                    except (asyncio.CancelledError, asyncio.InvalidStateError):
                        pass
                    _log.warning(
                        "TestSignalEngine: %s task exited unexpectedly%s — restarting",
                        name, f" ({exc})" if exc else "",
                    )
                    setattr(self, attr, asyncio.create_task(coro_fn()))

    # ── Fast price monitor ────────────────────────────────────────────────────

    async def _velocity_loop(self) -> None:
        """
        Samples price every _VELOCITY_INTERVAL seconds.  Fires an emergency scan
        (bypassing the candle gate) when either condition is met:

        1. Velocity spike: price moves >= _VELOCITY_THRESHOLD pts within
           _VELOCITY_WINDOW seconds — rapid directional move signals a potential
           reversal setup the candle gate would have missed entirely.

        2. Liquidity sweep: price touches/crosses a cached M15 swing high or low
           then reverses by >= _SWEEP_REVERSAL_PT pts within _SWEEP_TIMEOUT seconds
           — institutional stop-hunt followed by sharp rejection.
        """
        import collections
        _max_samples = int(_VELOCITY_WINDOW / _VELOCITY_INTERVAL) + 2
        _prices: collections.deque = collections.deque(maxlen=_max_samples)
        _prev_mid: float = 0.0
        _last_remote_check = 0.0
        _is_remote = False

        while self._running:
            try:
                # Unlike _run_cycle (which is naturally gated), this loop polls
                # the bridge independently every _VELOCITY_INTERVAL seconds —
                # re-check is_remote_node() on the same cadence as the candle
                # refresh below (not every iteration) so a VPS doesn't pay for
                # tick/candle polling it will never act on.
                _now_chk = time.time()
                if _now_chk - _last_remote_check >= _CANDLE_REFRESH_INTERVAL:
                    from forex_trader.core import database as _db_module
                    _is_remote = await _db_module.to_db_thread(_db_module.is_remote_node)
                    _last_remote_check = _now_chk
                if _is_remote:
                    await asyncio.sleep(_VELOCITY_INTERVAL)
                    continue

                tick = await self._bridge.get_tick()
                if tick:
                    mid = (float(tick.bid) + float(tick.ask)) / 2
                    now = time.time()
                    _prices.append((now, mid))

                    # ── 1. Velocity check ─────────────────────────────────────
                    window_start = now - _VELOCITY_WINDOW
                    window_prices = [(t, p) for t, p in _prices if t >= window_start]
                    if len(window_prices) >= 2:
                        oldest_px  = window_prices[0][1]
                        elapsed    = now - window_prices[0][0]
                        velocity   = abs(mid - oldest_px)
                        cooldown_ok = (now - self._last_emergency_scan) > _EMERGENCY_SCAN_COOLDOWN
                        if velocity >= _VELOCITY_THRESHOLD and cooldown_ok and not self._force_scan:
                            direction_lbl = "UP" if mid > oldest_px else "DOWN"
                            _log.info(
                                "[FastMonitor] Velocity spike %.2f pts in %.0fs (%s) — emergency scan queued",
                                velocity, elapsed, direction_lbl,
                            )
                            self._force_scan = True
                            if self._force_scan_event is not None:
                                self._force_scan_event.set()

                    # ── 2. Liquidity sweep check ──────────────────────────────
                    sh  = self._cached_swing_high
                    slo = self._cached_swing_low
                    cooldown_ok = (now - self._last_emergency_scan) > _EMERGENCY_SCAN_COOLDOWN

                    if sh > 0 and _prev_mid > 0:
                        # Swept swing HIGH — price touched/crossed it from below
                        if _prev_mid < sh and mid >= sh:
                            self._sweep_touch_high = mid
                            self._sweep_touch_time = now
                            _log.debug("[FastMonitor] Swing HIGH %.2f touched @ %.2f", sh, mid)

                    if self._sweep_touch_high > 0:
                        if (now - self._sweep_touch_time) > _SWEEP_TIMEOUT:
                            self._sweep_touch_high = 0.0
                        elif mid <= self._sweep_touch_high - _SWEEP_REVERSAL_PT:
                            if cooldown_ok and not self._force_scan:
                                _log.info(
                                    "[FastMonitor] Liquidity sweep HIGH %.2f → reversal to %.2f"
                                    " (%.2f pts) — emergency scan queued",
                                    self._sweep_touch_high, mid,
                                    self._sweep_touch_high - mid,
                                )
                                self._force_scan = True
                                if self._force_scan_event is not None:
                                    self._force_scan_event.set()
                            self._sweep_touch_high = 0.0

                    if slo > 0 and _prev_mid > 0:
                        # Swept swing LOW — price touched/crossed it from above
                        if _prev_mid > slo and mid <= slo:
                            self._sweep_touch_low = mid
                            self._sweep_touch_time = now
                            _log.debug("[FastMonitor] Swing LOW %.2f touched @ %.2f", slo, mid)

                    if self._sweep_touch_low > 0:
                        if (now - self._sweep_touch_time) > _SWEEP_TIMEOUT:
                            self._sweep_touch_low = 0.0
                        elif mid >= self._sweep_touch_low + _SWEEP_REVERSAL_PT:
                            if cooldown_ok and not self._force_scan:
                                _log.info(
                                    "[FastMonitor] Liquidity sweep LOW %.2f → reversal to %.2f"
                                    " (%.2f pts) — emergency scan queued",
                                    self._sweep_touch_low, mid,
                                    mid - self._sweep_touch_low,
                                )
                                self._force_scan = True
                                if self._force_scan_event is not None:
                                    self._force_scan_event.set()
                            self._sweep_touch_low = 0.0

                    _prev_mid = mid

                # ── Background candle cache refresh ───────────────────────────
                # Keeps fresh candle data ready so emergency scans skip the
                # bridge round-trip entirely and fire Claude sooner.
                if (now - self._last_candle_refresh) >= _CANDLE_REFRESH_INTERVAL:
                    try:
                        h1  = await self._bridge.get_candles("H1",  120)
                        m15 = await self._bridge.get_candles("M15",  60)
                        h4  = await self._bridge.get_candles("H4",   40)
                        m5  = await self._bridge.get_candles("M5",   30)
                        if h1 and m15:
                            _ts = time.time()
                            self._cached_candles = {
                                "H1":  (_ts, h1),
                                "M15": (_ts, m15),
                                "H4":  (_ts, h4 or []),
                                "M5":  (_ts, m5 or []),
                            }
                            # Keep swing levels fresh from the cache refresh too
                            _sh, _sl = _compute_swing_levels(m15)
                            if _sh > 0:
                                self._cached_swing_high = _sh
                            if _sl > 0:
                                self._cached_swing_low = _sl
                            self._last_candle_refresh = _ts
                    except Exception as _ce:
                        _log.debug("[FastMonitor] Candle cache refresh error: %s", _ce)

            except asyncio.CancelledError:
                break
            except Exception as e:
                _log.debug("[FastMonitor] velocity loop error: %s", e)

            await asyncio.sleep(_VELOCITY_INTERVAL)

    # ── Analysis cycle ────────────────────────────────────────────────────────

    async def _cycle_loop(self) -> None:
        while self._running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.error("Cycle error: %s", exc)
                self._status_detail = f"Error: {exc}"
            # Sleep up to _CYCLE_INTERVAL; wake instantly when force_scan fires.
            if self._force_scan_event is not None:
                try:
                    await asyncio.wait_for(
                        self._force_scan_event.wait(), timeout=_CYCLE_INTERVAL
                    )
                except asyncio.TimeoutError:
                    pass
                if self._running:
                    self._force_scan_event.clear()
            else:
                await asyncio.sleep(_CYCLE_INTERVAL)

    async def _run_cycle(self) -> None:
        # Centralized signal generation (Settings > Remote Node): once this
        # VPS is the active trader and generation has moved to the Mac, skip
        # the whole analysis cycle rather than running it and having its
        # eventual open_trade() call just get forwarded/rejected — this is
        # what actually saves the CPU on the VPS.
        from forex_trader.core import database as _db_module
        if await _db_module.to_db_thread(_db_module.is_remote_node):
            self._status = "Remote/VPS node — signal generation is local-node-only"
            return
        if not await _db_module.to_db_thread(_db_module.should_generate_signals_here):
            self._status = "Centralized mode: generation runs on the local node"
            return

        emergency = self._force_scan
        self._force_scan = False
        if emergency:
            self._last_emergency_scan = time.time()
        self._status = "analysing"
        log_entry: dict = {"ts": time.time()}



        # ── 2. Suppress conditions ────────────────────────────────────────────
        session = get_session()
        log_entry["session"] = session

        # Bootstrap ends at BOOTSTRAP_SAMPLES labeled examples (not ML_MIN_TRAIN_SAMPLES).
        # During bootstrap we still pass Claude rejections through so we collect training data;
        # after bootstrap, Claude rejections are fully enforced.
        _labeled = len(tdb.get_ml_training_data())
        _bootstrap = _labeled < ml.BOOTSTRAP_SAMPLES

        if session == "closed":
            reason = "Market closed — weekend"
            self._status_detail = reason
            self._status = "running"
            log_entry["suppressed_reason"] = reason
            tdb.log_analysis(log_entry)
            _log.debug(reason)
            return

        # Session gate — was previously generation-in-every-session (Asian
        # and "off" included) regardless of the Trading Markets toggles, on
        # the theory that off-session signals still had ML training value.
        # Changed on request: the toggles are now the single source of truth
        # for whether this engine analyses a given session at all, matching
        # GD Copy and Breakout.
        _sess_ok, _sess_name = await _db_module.to_db_thread(_db_module.is_session_allowed)
        if not _sess_ok:
            reason = f"Session '{_sess_name}' not enabled in Trading Markets"
            self._status_detail = reason
            self._status = "running"
            log_entry["suppressed_reason"] = reason
            tdb.log_analysis(log_entry)
            _log.debug(reason)
            return

        if is_news_window():
            reason = "News window active — suppressed"
            self._status_detail = reason
            self._status = "running"
            log_entry["suppressed_reason"] = reason
            tdb.log_analysis(log_entry)
            _log.debug(reason)
            return

        # Toxic-hour filter (measured, UTC 07, 12-16, 20 — see core/regime.py) now
        # lives in _execute_live() alongside the daily-loss circuit breaker — it
        # blocks real MT5 orders once hour_blocklist_enabled is on and the current
        # hour is in the blocked set, but signal generation/tracking continues
        # below regardless so the ML model keeps training on live market data
        # from those hours too (previously this returned here unconditionally,
        # meaning nothing was ever created or learned from during a blocked hour
        # — no user-facing on/off control either, just an internal adaptive
        # param defaulting to always-on). See _is_circuit_breaker_tripped().

        # ── 3. Fetch market data ──────────────────────────────────────────────
        try:
            tick = await self._bridge.get_tick()
            if not tick:
                self._status_detail = "No tick — bridge offline"
                self._status = "running"
                _log.warning("No tick from bridge")
                return

            # Spread gate — on gold the spread is a large fraction of a scalp's
            # TP1 distance; a widened spread (thin liquidity, news minutes)
            # silently doubles the entry cost, so hold new signals until it
            # normalises. Uses the same limit as the breakout engine.
            _spread = float(tick.ask) - float(tick.bid)
            _max_spread = ap.get("max_spread_pts")
            if _spread > _max_spread:
                reason = f"Spread {_spread:.2f} > {_max_spread:.2f} limit — suppressed"
                self._status_detail = reason
                self._status = "running"
                log_entry["suppressed_reason"] = reason
                tdb.log_analysis(log_entry)
                _log.debug(reason)
                return

            # Emergency scans use the velocity-loop candle cache if it's fresh,
            # saving ~200ms of bridge round-trips so Claude fires sooner.
            _cache_age = time.time() - min(
                (v[0] for v in self._cached_candles.values()), default=0.0
            ) if self._cached_candles else float("inf")

            if emergency and _cache_age <= _CANDLE_CACHE_MAX_AGE:
                h1_candles  = self._cached_candles["H1"][1]
                m15_candles = self._cached_candles["M15"][1]
                h4_candles  = self._cached_candles.get("H4", (0, []))[1]
                m5_candles  = self._cached_candles.get("M5", (0, []))[1]
                _log.debug("[TestSignal] Emergency scan using cached candles (age=%.1fs)", _cache_age)
            else:
                h1_candles  = await self._bridge.get_candles("H1",  120)
                m15_candles = await self._bridge.get_candles("M15",  60)
                h4_candles  = await self._bridge.get_candles("H4",   40)
                m5_candles  = await self._bridge.get_candles("M5",   30)
                # Update cache so next emergency scan has fresh data
                if h1_candles and m15_candles:
                    _ts = time.time()
                    self._cached_candles = {
                        "H1":  (_ts, h1_candles),
                        "M15": (_ts, m15_candles),
                        "H4":  (_ts, h4_candles or []),
                        "M5":  (_ts, m5_candles or []),
                    }
                    self._last_candle_refresh = _ts

            if not h1_candles or not m15_candles:
                self._status_detail = "No candle data"
                self._status = "running"
                return

        except Exception as e:
            self._status_detail = f"Bridge error: {e}"
            self._status = "running"
            _log.warning("Bridge fetch error: %s", e)
            return

        # Cache swing levels for the velocity/sweep monitor every time candles arrive
        sh, sl_swing = _compute_swing_levels(m15_candles)
        if sh > 0:
            self._cached_swing_high = sh
        if sl_swing > 0:
            self._cached_swing_low = sl_swing

        # ── 4. Gate on new candle close ───────────────────────────────────────
        # M15: main analysis (HTF bias, key levels, M15 patterns).
        # M5:  scalp trigger only — runs between M15 closes to maximise signal
        #      frequency during high-momentum windows (London 08-10 / NY 13-15).
        # Emergency: velocity spike or liquidity sweep detected — bypass gate.
        latest_m15_time = float(m15_candles[-1].get("ts", 0) or 0)
        latest_m5_time  = float(m5_candles[-1].get("ts", 0) or 0) if m5_candles else 0.0
        is_new_m15 = latest_m15_time > self._last_m15_candle_time
        is_new_m5  = bool(m5_candles) and (latest_m5_time > self._last_m5_candle_time)

        if not emergency and not is_new_m15 and not is_new_m5:
            self._status_detail = "Waiting for next candle close"
            self._status = "running"
            return

        if is_new_m15:
            self._last_m15_candle_time = latest_m15_time
        if is_new_m5:
            self._last_m5_candle_time = latest_m5_time
        if emergency:
            _log.info("[FastMonitor] Emergency scan — candle gate bypassed")

        current_price = float(tick.ask)
        atr_m15 = compute_atr(m15_candles[-20:], period=14)

        log_entry["price"]   = current_price
        log_entry["atr_m15"] = atr_m15

        # ── ATR collapse gate ──────────────────────────────────────────────────
        # Suppress signals when current volatility is significantly below its
        # recent baseline — dead-market chop (Asian gaps, pre-news consolidation)
        # where spread consumes the entire available range.
        if len(m15_candles) >= 50:
            _atr_ref = compute_atr(m15_candles[-50:-10], period=14)
            if _atr_ref > 0:
                try:
                    from forex_trader.core import database as _cdb_ac
                    _ac_thr = float(_cdb_ac.get_risk_settings().get("atr_collapse_threshold", 0.65))
                except Exception:
                    _ac_thr = 0.65
                _atr_ratio = atr_m15 / _atr_ref
                if _atr_ratio < _ac_thr:
                    reason = (
                        f"ATR collapse: {atr_m15:.1f} is {_atr_ratio:.0%} of baseline "
                        f"{_atr_ref:.1f} (<{_ac_thr:.0%}) — dead market suppressed"
                    )
                    self._status_detail = reason
                    log_entry.update({"suppressed_reason": reason, "result": "atr_collapse"})
                    tdb.log_analysis(log_entry)
                    _log.debug("[TestSignal] %s", reason)
                    self._status = "running"
                    self._last_cycle_at = time.time()
                    return

        # ── 5. HTF bias + H4 + indicators ────────────────────────────────────
        htf_bias = compute_htf_bias(h1_candles)
        h4_bias  = compute_h4_bias(h4_candles) if h4_candles else "neutral"
        atr_m5   = compute_atr(m5_candles[-15:], period=14) if m5_candles and len(m5_candles) >= 15 else 0.0
        m15_closes_all = [float(c.get("close", 0) or 0) for c in m15_candles]
        adx      = compute_adx(m15_candles)
        _, macd_hist = compute_macd_hist(m15_closes_all)
        # Compute MACD histogram for 3 and 6 bars ago so Claude can see the trend
        _, _macd_3 = compute_macd_hist(m15_closes_all[:-3]) if len(m15_closes_all) > 40 else (0.0, macd_hist)
        _, _macd_6 = compute_macd_hist(m15_closes_all[:-6]) if len(m15_closes_all) > 43 else (0.0, _macd_3)
        macd_hist_trend = [round(_macd_6, 4), round(_macd_3, 4), round(macd_hist, 4)]
        # 5-state day classification (core/regime.py) — replaces the old 3-state
        # detect_regime. M15 ADX catches acceleration; H1 efficiency ratio catches
        # steady grinds (like Jul 6) whose H1 ADX stayed deceptively low (~24)
        # while M15 ADX ran 43-52.
        from forex_trader.core.regime import classify_day, efficiency_ratio
        h1_closes = [float(c.get("close", 0) or 0) for c in h1_candles]
        h1_eff    = efficiency_ratio(h1_closes, n=24)
        regime    = classify_day(adx, h1_eff)
        log_entry["htf_bias"] = htf_bias
        log_entry["h4_bias"]  = h4_bias
        log_entry["adx"]      = round(adx, 1)
        log_entry["h1_eff"]   = h1_eff
        log_entry["regime"]   = regime

        # ── 6. Key levels ─────────────────────────────────────────────────────
        # Pass m15_candles so FVGs on M15 are included as entry levels
        key_levels = identify_key_levels(h1_candles, current_price, m15_candles=m15_candles)
        log_entry["key_levels"] = key_levels[:8]

        # ── 7. Entry trigger ──────────────────────────────────────────────────
        candidate = check_entry_trigger(
            m15_candles, h1_candles, key_levels, htf_bias, current_price, atr_m15,
            h4_bias=h4_bias, regime=regime, macd_hist=macd_hist, session=session,
        )
        # Fall back to M5 scalp trigger during high-momentum sessions
        if not candidate and m5_candles and atr_m5 > 0:
            candidate = check_scalp_trigger(
                m5_candles, key_levels, htf_bias, current_price, atr_m5, session
            )
        log_entry["candidate"] = candidate

        if not candidate:
            reason = "No entry trigger — no level touch with candle confirmation"
            self._status_detail = reason
            log_entry["suppressed_reason"] = reason
            log_entry["result"] = "no_trigger"
            tdb.log_analysis(log_entry)
            self._status = "running"
            self._last_cycle_at = time.time()
            return

        # Annotate candidate with computed indicators for downstream use
        candidate.setdefault("h4_bias",   h4_bias)
        candidate.setdefault("regime",    regime)
        candidate.setdefault("macd_hist", macd_hist)
        candidate.setdefault("adx",       adx)

        # ── 7a2. Extreme-trend gate for mean-reversion patterns ────────────────
        # Bounce and liquidity_sweep both assume a level holds and price reverts —
        # in a persistent, strongly trending market that assumption breaks down
        # regardless of trade direction (with-trend "bounces" keep getting run
        # through). Unlike the dual-bias gate below, this fires even for
        # with-trend signals and is not exempt for liquidity_sweep.
        _extreme_adx = ap.get("extreme_trend_adx")
        _extreme_trend = (
            htf_bias != "neutral" and h4_bias == htf_bias and adx >= _extreme_adx
        )
        if _extreme_trend and candidate.get("trigger_pattern") in ("bounce", "liquidity_sweep"):
            reason = (
                f"Extreme trend block: H1+H4 both {htf_bias}, ADX {adx:.0f} >= {_extreme_adx:.0f} "
                f"— {candidate['trigger_pattern']} pattern unsafe (levels don't hold in persistent trends)"
            )
            self._status_detail = reason
            log_entry["suppressed_reason"] = reason
            log_entry["result"] = "extreme_trend_block"
            tdb.log_analysis(log_entry)
            _log.debug("[TestSignal] %s", reason)
            self._status = "running"
            self._last_cycle_at = time.time()
            return

        # ── 7b. Dual-bias counter-trend gate ──────────────────────────────────
        # When H1 and H4 both agree on a trend direction AND ADX confirms trending,
        # block counter-trend signals at the rules layer (no Claude call wasted).
        # Exception: liquidity sweeps are always allowed — they ARE the institutional reversal.
        _db_threshold = ap.get("dual_bias_adx_block")
        _dual_bias_trending = (
            htf_bias != "neutral"
            and h4_bias == htf_bias
            and adx >= _db_threshold
        )
        if _dual_bias_trending:
            _is_counter = (
                (candidate["direction"] == "BUY"  and htf_bias == "bearish")
                or (candidate["direction"] == "SELL" and htf_bias == "bullish")
            )
            if _is_counter and candidate.get("trigger_pattern") != "liquidity_sweep":
                reason = (
                    f"Dual-bias block: H1+H4 both {htf_bias}, ADX {adx:.0f} ≥ {_db_threshold:.0f} "
                    f"— counter-trend {candidate['direction']} blocked"
                )
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "dual_bias_block"
                tdb.log_analysis(log_entry)
                _log.debug("[TestSignal] %s", reason)
                self._status = "running"
                self._last_cycle_at = time.time()
                return

        # ── 7c. Asian session: trend-aligned signals only ─────────────────────
        # During Asian session allow signals but only in the trend direction.
        # Counter-trend Asian signals have historically been the worst performers.
        if session == "asian" and htf_bias != "neutral":
            _asian_counter = (
                (candidate["direction"] == "BUY"  and htf_bias == "bearish")
                or (candidate["direction"] == "SELL" and htf_bias == "bullish")
            )
            if _asian_counter and candidate.get("trigger_pattern") != "liquidity_sweep":
                reason = (
                    f"Asian counter-bias block: HTF {htf_bias}, signal {candidate['direction']} — "
                    "only trend-aligned signals in Asian session"
                )
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "asian_bias_block"
                tdb.log_analysis(log_entry)
                _log.debug("[TestSignal] %s", reason)
                self._status = "running"
                self._last_cycle_at = time.time()
                return

        # ── 8. Risk levels ────────────────────────────────────────────────────
        direction = candidate["direction"]
        if candidate.get("is_scalp"):
            risk = calculate_scalp_risk_levels(candidate, atr_m5)
        else:
            risk = calculate_risk_levels(candidate, atr_m15, key_levels, direction, regime=regime)
        if not risk:
            reason = f"Risk calc failed — R:R below minimum for {direction}"
            self._status_detail = reason
            log_entry["suppressed_reason"] = reason
            log_entry["result"] = "rr_rejected"
            tdb.log_analysis(log_entry)
            self._status = "running"
            self._last_cycle_at = time.time()
            return

        candidate.update(risk)

        # ── 9a. Consecutive-loss direction cooldown ───────────────────────────
        try:
            with tdb._conn() as _cl_con:
                _cl_rows = _cl_con.execute(
                    "SELECT outcome FROM test_signals "
                    "WHERE direction=? AND close_time>? AND outcome IS NOT NULL "
                    "  AND outcome NOT IN ('open','pending') "
                    "ORDER BY close_time DESC LIMIT ?",
                    (direction, time.time() - _CONSEC_LOSS_WINDOW, _CONSEC_LOSS_LIMIT),
                ).fetchall()
            _cl_outcomes = [r[0] for r in _cl_rows]
            if len(_cl_outcomes) >= _CONSEC_LOSS_LIMIT and all(o == "loss" for o in _cl_outcomes):
                reason = (
                    f"Consecutive-loss cooldown: {_CONSEC_LOSS_LIMIT} consecutive {direction} "
                    f"losses in last {_CONSEC_LOSS_WINDOW // 3600}h — direction paused"
                )
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "consec_loss_cooldown"
                tdb.log_analysis(log_entry)
                _log.info("[TestSignal] %s", reason)
                self._status = "running"
                self._last_cycle_at = time.time()
                return
        except Exception as _cl_err:
            _log.debug("[TestSignal] Consecutive-loss check error: %s", _cl_err)

        # ── 9b. ML feature extraction ─────────────────────────────────────────
        # Inject cross-engine contextual features into candidate before ML extraction
        try:
            from forex_trader.core import database as _cdb_ctx
            from forex_trader.core.news_calendar import get_news_proximity_norm
            candidate["news_proximity_norm"]  = get_news_proximity_norm()
            candidate["equity_drawdown_pct"]  = _cdb_ctx.get_equity_drawdown_pct()
            candidate["concurrent_agreement"] = _cdb_ctx.get_concurrent_agreement("bounce", direction)
        except Exception:
            pass

        _market_ctx = mktctx.get_context()
        ml_features = ml.extract_features(
            m15_candles, h1_candles, candidate, key_levels, session, htf_bias, atr_m15,
            h4_bias=h4_bias, adx=adx, macd_hist=macd_hist, market_ctx=_market_ctx,
        )
        ml_pred = ml.predict(ml_features) if ml_features else None
        if ml_pred is not None:
            log_entry["ml_prob"] = round(float(ml_pred), 3)
            _log.debug("[TestSignal] ML predicted_R=%.3f", ml_pred)

        # ── 9c. ML R-multiple gate — block signals with negative predicted R ──
        if ml_pred is not None and ml.is_trained() and float(ml_pred) < _TS_ML_R_FLOOR and not _bootstrap:
            reason = f"ML gate: predicted_R={ml_pred:.3f} < {_TS_ML_R_FLOOR:.2f} floor"
            log_entry.update({"result": "ml_gate", "suppressed_reason": reason})
            tdb.log_analysis(log_entry)
            _log.info("[TestSignal] %s — skipping signal", reason)
            return

        # ── DXY opposing gate ─────────────────────────────────────────────────
        _dxy = _market_ctx.get("dxy_momentum", 0.0)
        _dxy_opposes = (
            (direction == "BUY"  and _dxy >  0.4) or
            (direction == "SELL" and _dxy < -0.4)
        )
        if _dxy_opposes and ml_pred is not None and ml.is_trained() and float(ml_pred) < 0.5 and not _bootstrap:
            reason = (
                f"DXY opposing gate: dxy_momentum={_dxy:+.2f} opposes {direction} — "
                f"ML predicted_R={ml_pred:.3f} < 0.5 required when DXY headwind active"
            )
            self._status_detail = reason
            log_entry.update({"result": "dxy_gate", "suppressed_reason": reason})
            tdb.log_analysis(log_entry)
            _log.info("[TestSignal] %s", reason)
            self._status = "running"
            self._last_cycle_at = time.time()
            return

        # ── 10. Claude quality gate (optional) ───────────────────────────────
        try:
            import forex_trader.core.database as _main_db_sg
            _sg_claude_on = bool(_main_db_sg.get_risk_settings().get("sg_claude_eval_enabled", 1))
        except Exception:
            _sg_claude_on = True

        # ── 9. Duplicate guard ────────────────────────────────────────────────
        open_sigs = tdb.get_open_signals()
        for sig in open_sigs:
            if (sig["direction"] == direction
                    and abs(sig["entry_mid"] - risk["entry_mid"]) < 30.0):
                reason = f"Duplicate: open {direction} signal near {sig['entry_mid']:.0f}"
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "duplicate"
                tdb.log_analysis(log_entry)
                self._status = "running"
                self._last_cycle_at = time.time()
                return

        # ── Cross-engine conflict suppression ─────────────────────────────────
        # window_seconds must not be shorter than realistic trade hold times —
        # a 180s (3min) window made genuinely still-open signals invisible once
        # they outlived it (measured medians: breakout 5.3min, bounce 8.4min),
        # letting this engine open straight into an opposing live position from
        # another engine. is_still_open (flipped by close_bus_entry the instant a
        # trade closes) is the correct authoritative signal; this window is now
        # just a crash/orphan safety net, not an active constraint.
        try:
            from forex_trader.core import database as _cdb_bus
            if _cdb_bus.has_conflict_on_bus("bounce", direction, window_seconds=21600.0):
                reason = f"Cross-engine conflict: opposite-direction signal active on bus for {direction}"
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "conflict_suppressed"
                tdb.log_analysis(log_entry)
                _log.info("[TestSignal] %s", reason)
                self._status = "running"
                self._last_cycle_at = time.time()
                return
        except Exception:
            pass

        if _sg_claude_on:
            cfg        = cfg_module.load()
            m15_closes = [float(c.get("close", 0) or 0) for c in m15_candles[-10:]]
            tg_context = _fetch_recent_tg_signals()
            _t0_claude = time.time()
            review = await review_signal(
                candidate, htf_bias, session, key_levels, m15_closes, cfg,
                tg_signals=tg_context,
                ml_prob=ml_pred,
                trigger_pattern=candidate.get("trigger_pattern", "bounce"),
                h4_bias=h4_bias,
                adx=adx,
                macd_hist=macd_hist,
                macd_hist_trend=macd_hist_trend,
                regime=regime,
            )
            _log.debug("[TestSignal] Claude gate took %.2fs", time.time() - _t0_claude)
            log_entry["claude_decision"] = review.get("rationale", "")
            _log.info("[TestSignal] Claude: approved=%s score=%.2f conf=%s — %s",
                      review.get("approved"), review.get("quality_score", 0),
                      review.get("confidence"), review.get("rationale"))
        else:
            review = {
                "approved": True, "quality_score": 0.70, "confidence": "low",
                "rationale": "Claude eval disabled — ML+rules passed",
                "_is_fallback": False,
            }
            log_entry["claude_decision"] = review["rationale"]
            _log.info("[TestSignal] Claude eval OFF — auto-approved")

        if not review.get("approved", True):
            if _bootstrap:
                # During bootstrap, log Claude's opinion but accept the signal anyway so we
                # accumulate labeled training examples.  Counter-trend signals were already
                # blocked by the dual-bias and Asian gates above, so bootstrap data quality
                # is now substantially better than the previous version.
                _log.info(
                    "[TestSignal] Bootstrap: Claude rejected but overriding "
                    "(%d/%d samples). Rationale: %s",
                    _labeled, ml.BOOTSTRAP_SAMPLES, review.get("rationale"),
                )
                log_entry["claude_decision"] = (
                    "[BOOTSTRAP-OVERRIDE] " + review.get("rationale", "")
                )
            else:
                reason = f"Claude rejected: {review.get('rationale', '')}"
                self._status_detail = reason
                log_entry["suppressed_reason"] = reason
                log_entry["result"] = "claude_rejected"
                tdb.log_analysis(log_entry)
                _log.info("[TestSignal] Signal rejected by Claude: %s", review.get("rationale"))
                self._status = "running"
                self._last_cycle_at = time.time()
                return

        quality_score = float(review.get("quality_score", 0.5))
        min_q = ap.get("min_quality_score", regime=regime)
        if quality_score < min_q and not _bootstrap:
            reason = (f"Quality score {quality_score:.0%} below threshold "
                      f"{min_q:.0%} — skipped")
            self._status_detail = reason
            log_entry["suppressed_reason"] = reason
            log_entry["result"] = "quality_low"
            tdb.log_analysis(log_entry)
            _log.info("[TestSignal] Signal skipped (quality %.2f < %.2f)", quality_score, min_q)
            self._status = "running"
            self._last_cycle_at = time.time()
            return

        # ── 11. Position sizing — mirrors live account (1:500 leverage, Vantage) ──
        balance  = tdb.get_virtual_balance()
        sl_dist  = float(risk.get("sl_dist", atr_m15))

        # Fixed 0.1 lot size at 1:500 leverage — independent of main app settings.
        try:
            from forex_trader.core.database import get_risk_settings
            rs = get_risk_settings()
            active_strategy = rs.get("trade_strategy", "be_runner")
        except Exception:
            active_strategy = "be_runner"

        lot_size, risk_amount = _calc_lot_size(
            balance, sl_dist, risk_pct=_RISK_PCT, fixed_lot=_FIXED_LOT
        )

        # ── 12. (strategy already read above) ────────────────────────────────

        # ── 13. Store signal ──────────────────────────────────────────────────
        sig_record = {
            "created_at":      time.time(),
            "direction":       direction,
            "entry_low":       risk["entry_low"],
            "entry_high":      risk["entry_high"],
            "entry_mid":       risk["entry_mid"],
            "stop_loss":       risk["stop_loss"],
            "tp1":             risk.get("tp1"),
            "tp2":             risk.get("tp2"),
            "tp3":             risk.get("tp3"),
            "sl_dist":         risk.get("sl_dist"),
            "rr_tp1":          risk.get("rr_tp1"),
            "rr_tp3":          risk.get("rr_tp3"),
            "session":         session,
            "htf_bias":        htf_bias,
            "atr_m15":         atr_m15,
            "key_level":       candidate.get("key_level"),
            "key_level_type":  candidate.get("key_level_type"),
            "rationale":       review.get("rationale", ""),
            "quality_score":   quality_score,
            "claude_approved":  review.get("approved", True),
            "claude_fallback":  1 if review.get("_is_fallback") else 0,
            "lot_size":         lot_size,
            "risk_amount":      risk_amount,
            "trigger_pattern":  candidate.get("trigger_pattern", ""),
            "strategy":         active_strategy,
            "ml_prob":          ml_pred,
            "regime":           candidate.get("regime", regime),
            "adx":              candidate.get("adx", adx),
        }
        signal_id, signal_ref = tdb.insert_signal(sig_record)

        if ml_features:
            tdb.store_ml_features(signal_id, ml_features)

        # Write to signal bus for cross-engine conflict/confluence detection.
        # ttl_seconds is a crash/orphan safety net only — real closure is
        # signalled by close_bus_entry(), so the TTL must comfortably outlive
        # any realistic trade hold time or it expires the entry (and stops
        # protecting against conflicts) while the trade is still genuinely open.
        try:
            from forex_trader.core import database as _cdb_bus2
            _cdb_bus2.write_signal_bus(
                "bounce", direction,
                confidence=float(ml_pred) if ml_pred is not None else 0.5,
                signal_id=signal_id,
                ttl_seconds=21600.0,
            )
        except Exception:
            pass

        log_entry["result"] = f"signal_created {signal_ref}"
        tdb.log_analysis(log_entry)

        _log.info(
            "[TestSignal] NEW SIGNAL %s %s @ %.2f–%.2f SL=%.2f TP1=%.2f TP3=%.2f "
            "R:R=%.2f lot=%.2f risk=$%.2f session=%s bias=%s strategy=%s",
            signal_ref, direction,
            risk["entry_low"], risk["entry_high"],
            risk["stop_loss"], risk.get("tp1", 0), risk.get("tp3", 0),
            risk.get("rr_tp1", 0), lot_size, risk_amount,
            session, htf_bias, active_strategy,
        )
        self._status_detail = (
            f"{signal_ref} {direction} @ {risk['entry_mid']:.2f} "
            f"lot={lot_size} risk=${risk_amount:.2f}"
        )
        self._status = "running"
        self._last_cycle_at = time.time()
        self._notify_refresh()

    # ── Outcome tracking ──────────────────────────────────────────────────────

    async def _outcome_loop(self) -> None:
        while self._running:
            try:
                await self._check_outcomes()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.debug("Outcome loop error: %s", exc)
            await asyncio.sleep(_OUTCOME_INTERVAL)

    async def _check_outcomes(self) -> None:
        open_sigs = tdb.get_open_signals()
        if not open_sigs:
            tdb.expire_old_pending_signals(_SIGNAL_MAX_AGE_H)
            return

        now = time.time()

        try:
            tick = await self._bridge.get_tick()
        except Exception:
            return
        if not tick:
            return

        bid = float(tick.bid)
        ask = float(tick.ask)
        spread_raw = ask - bid
        notify = False

        # Check live execution settings once per cycle
        _sg_live = False
        if self._main_engine is not None:
            try:
                from forex_trader.core import database as _main_db
                _main_rs = _main_db.get_risk_settings()
                _sg_live = bool(_main_rs.get("sg_live_execution", 0))
            except Exception:
                pass

        for sig in open_sigs:
            sid       = sig["id"]
            direction = sig["direction"].upper()
            sl        = float(sig["stop_loss"] or 0)
            tp1       = sig.get("tp1")
            tp3       = sig.get("tp3")
            entry_mid = float(sig["entry_mid"] or 0)
            lot_size  = float(sig.get("lot_size") or _MIN_LOT)
            sl_moved  = bool(sig.get("sl_moved_to_be"))

            current = bid if direction == "BUY" else ask

            # ── Live-execution closure sync ───────────────────────────────────
            # For be_runner / scale_out, after TP1 the SL moves to BE and the
            # engine waits for TP3. If the main engine closes the live MT5 trade
            # between TP1 and TP3, neither the BE-SL nor the TP3 check fires and
            # the signal gets permanently stuck as "triggered". Detect this by
            # polling the main DB whenever the signal has a linked MT5 ticket.
            if sig.get("status") == "triggered" and sig.get("mt5_ticket") and sig.get("live_exec_status") == "success":
                try:
                    from forex_trader.core import database as _mdb

                    def _fetch_mt5_close():
                        import sqlite3 as _sl3
                        with _sl3.connect(f"file:{_mdb._DB_PATH}?mode=ro", uri=True) as _mc:
                            _mc.row_factory = _sl3.Row
                            return _mc.execute(
                                "SELECT status, mt5_profit, net_pnl FROM vantage_simulated_trades "
                                "WHERE mt5_ticket=? AND status='closed'",
                                (sig["mt5_ticket"],),
                            ).fetchone()

                    # Offloaded — a raw sqlite3.connect() here blocked the whole
                    # event loop under DB contention (see _reconcile_live_pnl).
                    _mrow = await _mdb.to_db_thread(_fetch_mt5_close)
                    if _mrow:
                        _profit = float(_mrow["mt5_profit"] or _mrow["net_pnl"] or 0)
                        _mt5_outcome = "win" if _profit > 1.0 else ("loss" if _profit < -1.0 else "be")
                        _close_px = current  # best available approximation
                        _pnl_pts  = round(
                            (_close_px - entry_mid) if direction == "BUY" else (entry_mid - _close_px), 2
                        )
                        _log.info(
                            "[TestSignal] %s closed via MT5 sync: profit=%.2f → %s",
                            sig.get("signal_ref", f"SIG-{sid:04d}"), _profit, _mt5_outcome,
                        )
                        await self._close_signal(
                            sid, _mt5_outcome, _close_px, _pnl_pts, lot_size, direction, spread=spread_raw
                        )
                        notify = True
                        continue
                except Exception as _sync_exc:
                    _log.debug("[TestSignal] MT5 closure sync failed for SIG-%04d: %s", sid, _sync_exc)

            # Live-executed signals must only be closed via the MT5 sync above.
            # Skipping virtual SL/TP here ensures the balance reflects the real
            # MT5 profit rather than a fabricated price at evaluation time.
            if sig.get("live_exec_status") == "success" and sig.get("status") == "triggered":
                continue

            # ── Trigger pending signal when price enters entry zone ────────────
            if sig["status"] == "pending":
                zone_low  = float(sig["entry_low"]  or entry_mid)
                zone_high = float(sig["entry_high"] or entry_mid)
                atr_m15   = float(sig.get("atr_m15") or 1.0)
                in_zone_buy  = direction == "BUY"  and ask <= zone_high
                in_zone_sell = direction == "SELL" and bid >= zone_low
                in_zone = in_zone_buy or in_zone_sell

                if in_zone:
                    # Increment dwell counter each cycle price remains in zone
                    self._zone_dwell[sid] = self._zone_dwell.get(sid, 0) + 1
                    dwell = self._zone_dwell[sid]

                    if dwell < _MIN_ZONE_DWELL:
                        # Price entered zone but hasn't dwelt long enough yet
                        _log.debug(
                            "[TestSignal] SIG-%04d in zone (dwell %d/%d) — waiting",
                            sid, dwell, _MIN_ZONE_DWELL,
                        )
                        continue

                    # Session gate — hold in zone but don't trigger if market not selected
                    from forex_trader.core.database import is_session_allowed as _isa
                    _sess_ok, _sess_name = _isa()
                    if not _sess_ok:
                        _log.debug(
                            "[TestSignal] SIG-%04d in zone but session '%s' not enabled — holding",
                            sid, _sess_name,
                        )
                        continue

                    # Dwell threshold met and session OK — trigger the signal
                    fill_px = ask if direction == "BUY" else bid
                    tdb.update_signal_triggered(sid, fill_px)

                    # Patch ML features with actual trigger drift (replaces creation placeholder)
                    drift_atr = abs(fill_px - entry_mid) / atr_m15 if atr_m15 > 0 else 0.5
                    tdb.patch_ml_features(sid, {"trigger_drift_atr": round(drift_atr, 4)})

                    self._zone_dwell.pop(sid, None)
                    _log.info(
                        "[TestSignal] SIG-%04d %s triggered @ %.2f (dwell %d cycles, drift %.2f atr)",
                        sid, direction, fill_px, dwell, drift_atr,
                    )
                    if _sg_live:
                        await self._execute_live(sig, fill_px, tick)
                    notify = True
                else:
                    # Price left the zone — reset dwell counter
                    if sid in self._zone_dwell:
                        self._zone_dwell.pop(sid)
                continue

            if sig["status"] != "triggered":
                continue

            # Orphan watchdog: live execution was enabled at trigger time but
            # live_exec_status was never written — happens when the process
            # crashed or restarted exactly during _execute_live. After 2 min
            # the signal is confirmed orphaned; mark it so the UI shows a
            # reason rather than leaving it silent indefinitely.
            trigger_time = float(sig.get("trigger_time") or 0)
            if (_sg_live
                    and trigger_time > 0
                    and not sig.get("live_exec_status")
                    and (now - trigger_time) > 120):
                tdb.update_live_exec_result(
                    sig["id"], None, None, "failed:orphaned_no_response"
                )
                _log.warning(
                    "[TestSignal] SIG-%04d triggered %ds ago with live mode on but "
                    "live_exec_status never written — marking orphaned",
                    sid, int(now - trigger_time),
                )

            trigger_price = float(sig.get("trigger_price") or entry_mid)
            strategy = (sig.get("strategy") or "be_runner").lower()

            # Conservative strategy uses fixed-point TP1/SL from the actual fill
            # price, ignoring the ATR-based levels set at signal creation.
            #   conservative:       SL 5pt / TP1 3pt
            #   conservative_trial: SL 5pt / TP1 5pt  (unchanged — trial keeps 5pt)
            _CONSERVATIVE_STRATS = {"conservative", "conservative_trial"}
            if strategy == "conservative":
                _CO_SL_PT, _CO_TP1_PT = 5.0, 3.0
            else:  # conservative_trial
                _CO_SL_PT, _CO_TP1_PT = 5.0, 5.0
            if strategy in _CONSERVATIVE_STRATS and trigger_price:
                if direction == "BUY":
                    tp1 = str(trigger_price + _CO_TP1_PT)
                    sl  = trigger_price - _CO_SL_PT
                else:
                    tp1 = str(trigger_price - _CO_TP1_PT)
                    sl  = trigger_price + _CO_SL_PT
                # Persist the override so history columns show the actual SL/TP1 used.
                _db_sl  = float(sig.get("stop_loss") or 0)
                _db_tp1 = float(sig.get("tp1") or 0)
                if abs(_db_sl - sl) > 0.001 or abs(_db_tp1 - float(tp1)) > 0.001:
                    tdb.update_conservative_levels(sid, sl, float(tp1))

            # ── Early breakeven + time stop (payoff-ratio repair) ─────────────
            # Measured: realized payoff was 0.65:1 because the TP1-gated BE move
            # never engaged on a single loss (0/117) — losses run the full stop
            # in ~26min while winners are positive well before. Two fixes:
            #   1. move SL to BE+cost at a fraction of the stop distance
            #   2. cut any trade still flat/negative after time_stop_mins
            _sig_regime = sig.get("regime") or None
            if strategy not in _CONSERVATIVE_STRATS and trigger_price:
                _unreal = round(
                    (current - trigger_price) if direction == "BUY"
                    else (trigger_price - current), 2,
                )
                _sl_dist_v = float(sig.get("sl_dist") or 0) or abs(trigger_price - sl)

                if (not sl_moved and _sl_dist_v > 0
                        and _unreal >= _sl_dist_v * ap.get("early_be_frac", regime=_sig_regime)):
                    _be_cost = _compute_cost_pts(spread_raw)
                    _be_px = round(
                        trigger_price + _be_cost if direction == "BUY"
                        else trigger_price - _be_cost, 2,
                    )
                    tdb.set_signal_sl_moved(sid, _be_px)
                    sl = _be_px
                    sl_moved = True
                    notify = True
                    _log.info(
                        "[TestSignal] SIG-%04d early BE @ +%.1fpts (%.0f%% of SL dist)",
                        sid, _unreal, ap.get("early_be_frac", regime=_sig_regime) * 100,
                    )

                _ts_mins = ap.get("time_stop_mins", regime=_sig_regime)
                if (trigger_time > 0 and (now - trigger_time) > _ts_mins * 60
                        and _unreal < 1.0):
                    close_px = current
                    outcome = "loss" if _unreal < -1.0 else "be"
                    _log.info(
                        "[TestSignal] SIG-%04d time stop after %.0fmin @ %+.1fpts → %s",
                        sid, (now - trigger_time) / 60, _unreal, outcome,
                    )
                    await self._close_signal(
                        sid, outcome, close_px, _unreal, lot_size, direction, spread=spread_raw
                    )
                    notify = True
                    continue

            # ── SL hit ────────────────────────────────────────────────────────
            if sl > 0:
                sl_hit = (direction == "BUY" and bid <= sl) or (direction == "SELL" and ask >= sl)
                if sl_hit:
                    close_px = sl
                    pnl_pts  = round(sl - trigger_price, 2) if direction == "BUY" else round(trigger_price - sl, 2)
                    outcome  = "be" if sl_moved else "loss"
                    await self._close_signal(sid, outcome, close_px, pnl_pts, lot_size, direction, spread=spread_raw)
                    notify = True
                    continue

            # ── TP1 hit ───────────────────────────────────────────────────────
            if tp1 and not sl_moved:
                tp1f    = float(tp1)
                tp1_hit = (direction == "BUY" and bid >= tp1f) or (direction == "SELL" and ask <= tp1f)
                if tp1_hit:
                    if strategy in _CONSERVATIVE_STRATS:
                        # Conservative closes the full position at TP1.
                        close_px = tp1f
                        pnl_pts  = round(tp1f - trigger_price, 2) if direction == "BUY" else round(trigger_price - tp1f, 2)
                        await self._close_signal(sid, "win", close_px, pnl_pts, lot_size, direction, spread=spread_raw)
                        notify = True
                        continue
                    else:
                        # be_runner / scale_out: TP1 hit moves SL to break-even
                        # PLUS the round-trip cost — a raw-entry BE quietly loses
                        # spread+commission on every 'be' close (avg -$8.83 per
                        # BE exit across the engines before this fix).
                        _be_cost = _compute_cost_pts(spread_raw)
                        _be_px = round(
                            trigger_price + _be_cost if direction == "BUY"
                            else trigger_price - _be_cost, 2,
                        )
                        tdb.set_signal_sl_moved(sid, _be_px)
                        sl_moved = True
                        notify   = True
                        # Fall through — TP3 check may also fire this cycle.

            # ── TP3 hit — full winner (be_runner after TP1, or direct TP3 hit) ─
            if tp3 and strategy not in _CONSERVATIVE_STRATS:
                tp3f    = float(tp3)
                tp3_hit = (direction == "BUY" and bid >= tp3f) or (direction == "SELL" and ask <= tp3f)
                if tp3_hit:
                    close_px = tp3f
                    pnl_pts  = round(tp3f - trigger_price, 2) if direction == "BUY" else round(trigger_price - tp3f, 2)
                    await self._close_signal(sid, "win", close_px, pnl_pts, lot_size, direction, spread=spread_raw)
                    notify = True
                    continue

        if notify:
            self._notify_refresh()

        tdb.expire_old_pending_signals(_SIGNAL_MAX_AGE_H)

    async def _close_signal(self, signal_id: int, outcome: str, close_px: float,
                            pnl_pts: float, lot_size: float, direction: str,
                            spread: float = 0.30) -> None:
        # Clear the signal bus entry immediately so other engines see it as resolved
        try:
            from forex_trader.core import database as _cdb_bus_close
            _cdb_bus_close.close_bus_entry("bounce", signal_id)
        except Exception:
            pass

        # Gross P&L (price-level based, no costs)
        pnl_dollars = _calc_pnl_dollars(pnl_pts, lot_size)

        # Cost-adjusted P&L — what a real trader actually nets after spread/commission/slippage
        cost_pts      = _compute_cost_pts(spread)
        net_pnl_pts   = round(pnl_pts - cost_pts, 4)
        net_pnl_dol   = _calc_pnl_dollars(net_pnl_pts, lot_size)

        # Update virtual balance with net P&L (cost-realistic)
        balance = tdb.get_virtual_balance()
        new_balance = round(balance + net_pnl_dol, 2)
        tdb.set_virtual_balance(new_balance)
        ref = f"SIG-{signal_id:04d}"
        tdb.log_balance(new_balance, net_pnl_dol, f"{outcome} {ref} {direction}", signal_id)

        learning_note = await self._generate_learning_note(signal_id, outcome, pnl_pts, net_pnl_dol)

        tdb.update_signal_status(
            signal_id, "closed", outcome, close_px, pnl_pts,
            pnl_dollars=net_pnl_dol, balance_after=new_balance,
            learning_note=learning_note,
        )

        ref = f"SIG-{signal_id:04d}"
        _log.info(
            "[TestSignal] %s %s CLOSED %s gross_pts=%.2f net_pts=%.2f pnl_$=%.2f balance=$%.2f",
            ref, direction, outcome.upper(), pnl_pts, net_pnl_pts, net_pnl_dol, new_balance,
        )

        try:
            from forex_trader.sync.ledger import push_trade_closed
            _sig_for_ledger = tdb.get_signal_by_id(signal_id)
            push_trade_closed({
                "trade_id":    ref,
                "engine":      "bounce",
                "direction":   direction,
                "strategy":    (_sig_for_ledger or {}).get("strategy", ""),
                "open_time":   (_sig_for_ledger or {}).get("created_at"),
                "close_time":  time.time(),
                "tg_source":   "Bounce Generator",
                "mt5_ticket":  (_sig_for_ledger or {}).get("mt5_ticket"),
                "pnl_dollars": net_pnl_dol,
                "outcome":     outcome,
            })
        except Exception as _le:
            _log.debug("[Ledger] push failed: %s", _le)

        # If live execution was used, resolve the actual MT5 P&L immediately.
        _mt5_outcome_resolved = False
        sig_row = tdb.get_signal_by_id(signal_id)
        mt5_ticket = sig_row.get("mt5_ticket") if sig_row else None
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
                    outcome = (
                        "win"  if actual_profit > 1.0  else
                        "loss" if actual_profit < -1.0 else
                        "be"
                    )
                    tdb.update_signal_pnl_from_mt5(signal_id, actual_profit, outcome)
                    _mt5_outcome_resolved = True
                    _log.debug(
                        "[TestSignal] SIG-%04d resolved to MT5 profit $%.2f (%s)",
                        signal_id, actual_profit, outcome,
                    )
            except Exception as _e:
                _log.debug("[TestSignal] MT5 P&L lookup failed for sig %d: %s", signal_id, _e)

        # ML outcome: re-classify as "loss" if virtual costs flip a marginal win/be
        # into a net loss — but only when the outcome is not already grounded in
        # the real MT5 profit (virtual net_pnl_pts would use an approximated price).
        ml_outcome = outcome
        if not _mt5_outcome_resolved and outcome in ("win", "be") and net_pnl_pts <= 0:
            ml_outcome = "loss"
        ml.record_outcome(signal_id, ml_outcome)

        self._closed_trade_count += 1

        # Batch learning every N closed trades
        if self._closed_trade_count % _BATCH_REVIEW_EVERY == 0:
            asyncio.create_task(self._run_batch_analysis())

    async def _execute_live(self, sig: dict, fill_px: float, tick) -> None:
        """
        Place a real MT5 trade via the main engine when sg_live_execution is ON.
        The main engine handles strategy overrides (e.g. conservative 5pt TP),
        Risk Governor, Telegram notifications, History, and all stats.
        The virtual signal continues to track its own outcome independently.
        """
        sig_id     = sig.get("id")
        signal_ref = sig.get("signal_ref") or f"SIG-{sig_id or 0:04d}"
        direction  = sig["direction"].upper()

        if self._main_engine is None:
            _log.warning("[LiveExec] %s skipped — main engine not linked", signal_ref)
            if sig_id:
                tdb.update_live_exec_result(sig_id, None, None, "skipped:no_main_engine")
            return

        # Toxic-hour blocklist: blocks real money only — the signal above
        # this call still generated and will still track/close/train
        # normally. Trading > Strategy > Risk Settings toggle, shared with
        # the Breakout generator, off by default.
        from forex_trader.core import database as _cdb_hour
        if bool(_cdb_hour.get_risk_settings().get("hour_blocklist_enabled", 0)):
            from forex_trader.core.regime import BOUNCE_BLOCKED_HOURS_UTC
            _hour_now = datetime.now(timezone.utc).hour
            if _hour_now in BOUNCE_BLOCKED_HOURS_UTC:
                reason = f"hour_blocklist: {_hour_now:02d} UTC (measured negative expectancy)"
                _log.info("[LiveExec] %s skipped — %s", signal_ref, reason)
                if sig_id:
                    tdb.update_live_exec_result(sig_id, None, None, f"skipped:{reason}")
                return

        vantage_sig_id = None
        try:
            # Sort TPs into valid direction order before passing to the main engine.
            _raw = [sig.get(k) for k in ("tp1","tp2","tp3","tp4","tp5","tp6","tp7","tp8")]
            _sorted = sorted((t for t in _raw if t is not None), reverse=(direction == "SELL"))
            while len(_sorted) < 8:
                _sorted.append(None)
            tp1, tp2, tp3, tp4, tp5, tp6, tp7, tp8 = _sorted

            # Scale lot size by ML confidence: 0.5x at low confidence, 1.0x at 0.5,
            # up to 1.3x at high confidence. Only applies when model is trained.
            base_lot = float(sig.get("lot_size") or 0)
            if base_lot > 0:
                # Confidence sizing capped to 0.75-1.15x (was 0.5-1.3x): measured
                # dollar PnL was asymmetric vs point PnL, meaning the wider range
                # was systematically up-sizing the losing trades.
                _ml_r = sig.get("ml_prob")  # R-multiple prediction
                if _ml_r is not None and ml.is_trained():
                    ml_scale = round(max(0.75, min(1.15, 0.5 + float(_ml_r) * 0.4)), 2)
                else:
                    _q = sig.get("quality_score")
                    ml_scale = round(max(0.75, min(1.15, 0.5 + float(_q))), 2) if _q is not None else 1.0
                base_lot = round(base_lot * ml_scale, 2)

            # Kelly Criterion fractional sizing — adjusts lot by rolling win-rate edge
            try:
                from forex_trader.core import database as _cdb_kelly
                if bool(_cdb_kelly.get_risk_settings().get("kelly_sizing_enabled", 0)):
                    _recent = tdb.get_recent_closed_signals(limit=50)
                    _wins   = [s for s in _recent if s.get("outcome") == "win"]
                    _losses = [s for s in _recent if s.get("outcome") == "loss"]
                    _n      = len(_wins) + len(_losses)
                    if _n >= 20 and _wins and _losses:
                        _avg_w = sum(s.get("pnl_pts", 0) or 0 for s in _wins)  / len(_wins)
                        _avg_l = abs(sum(s.get("pnl_pts", 0) or 0 for s in _losses) / len(_losses))
                        if _avg_l > 0 and _avg_w > 0:
                            _wr  = len(_wins) / _n
                            _R   = _avg_w / _avg_l
                            _kf  = _wr - (1 - _wr) / _R   # Kelly fraction
                            _hk  = _kf / 2                  # half-Kelly for safety
                            _km  = round(max(0.75, min(1.25, 1.0 + _hk)), 2)
                            base_lot = round(base_lot * _km, 2)
                            _log.info(
                                "[LiveExec] Kelly: wr=%.0f%% R=%.2f f=%.3f mult=%.2f lot→%.2f",
                                _wr * 100, _R, _kf, _km, base_lot,
                            )
            except Exception as _ke:
                _log.debug("[LiveExec] Kelly sizing error: %s", _ke)

            main_sig = self._main_engine.create_signal(
                source_name = "Bounce Generator",
                direction   = direction,
                entry_low   = float(sig["entry_low"]),
                entry_high  = float(sig["entry_high"]),
                stop_loss   = float(sig["stop_loss"]),
                tp1=tp1, tp2=tp2, tp3=tp3, tp4=tp4, tp5=tp5, tp6=tp6, tp7=tp7, tp8=tp8,
                lot_size = base_lot,
                notes    = signal_ref,
            )
            vantage_sig_id = main_sig["signal_id"]
            result = await self._main_engine.open_trade_from_signal(vantage_sig_id, tick=tick)
            mt5_ticket = result.get("mt5_ticket")
            _log.info(
                "[LiveExec] %s %s live trade opened: ticket=%s entry=%.2f",
                signal_ref, direction, mt5_ticket, result.get("entry_price", fill_px),
            )
            if sig_id:
                tdb.update_live_exec_result(sig_id, mt5_ticket, vantage_sig_id, "success")
        except Exception as exc:
            reason = str(exc)[:120]
            _log.warning("[LiveExec] %s live trade failed: %s", signal_ref, reason)
            if sig_id:
                tdb.update_live_exec_result(sig_id, None, vantage_sig_id, f"failed:{reason}")

    async def _generate_learning_note(self, signal_id: int, outcome: str,
                                      pnl_pts: float, pnl_dollars: float) -> str:
        """Ask the configured AI provider for a one-line post-trade explanation."""
        cfg = cfg_module.load()
        if not ai_provider.is_configured(cfg):
            return ""

        try:
            sig = tdb.get_signal_by_id(signal_id)
            if not sig:
                return ""

            prompt = (
                f"Trade closed: {sig.get('direction')} XAUUSD\n"
                f"Outcome: {outcome}  PnL: {pnl_pts:+.2f} pts (${pnl_dollars:+.2f})\n"
                f"Entry: ${sig.get('entry_mid', 0):.2f}  SL: ${sig.get('stop_loss', 0):.2f}  "
                f"TP1: ${sig.get('tp1') or 0:.2f}  TP3: ${sig.get('tp3') or 0:.2f}\n"
                f"Session: {sig.get('session')}  HTF bias: {sig.get('htf_bias')}\n"
                f"Key level type: {sig.get('key_level_type')}  "
                f"Quality score: {sig.get('quality_score', 0):.0%}\n"
                f"Signal rationale: {sig.get('rationale', '')}\n\n"
                "In ONE sentence, explain the most likely reason this trade won or lost "
                "and the single most important improvement for future signals of this type."
            )
            return await ai_provider.complete(cfg, "", prompt, max_tokens=120, timeout=15)
        except Exception as e:
            _log.debug("[TestSignal] Learning note error: %s", e)
            return ""

    async def _run_batch_analysis(self) -> None:
        """
        Every _BATCH_REVIEW_EVERY trades, ask Claude to analyse patterns and
        recommend specific parameter adjustments.  Adjustments are applied
        automatically (clamped to safe ranges) and logged.
        """
        cfg = cfg_module.load()
        if not ai_provider.is_configured(cfg):
            return

        recent = tdb.get_recent_closed_signals(limit=_BATCH_REVIEW_EVERY)
        if len(recent) < 3:
            return

        balance   = tdb.get_virtual_balance()
        stats     = tdb.get_stats()
        by_sess   = tdb.get_perf_by_session()
        by_level  = tdb.get_perf_by_level_type()
        by_bias   = tdb.get_perf_by_bias()
        tg_rows   = _fetch_tg_outcomes()

        trade_lines = []
        by_regime: dict[str, dict] = {}
        for s in recent:
            ref = s.get("signal_ref") or f"SIG-{s['id']:04d}"
            fallback_flag = " [fallback-approved]" if s.get("claude_fallback") else ""
            regime = s.get("regime") or "neutral"
            trade_lines.append(
                f"  {ref} {s.get('direction')} {(s.get('outcome') or '?').upper():6s}  "
                f"pnl={s.get('pnl_pts', 0):+.1f}pts (${s.get('pnl_dollars', 0):+.2f})  "
                f"session={s.get('session')}  bias={s.get('htf_bias')}  regime={regime} "
                f"adx={s.get('adx') or 0:.0f}  "
                f"level={s.get('key_level_type')}  quality={s.get('quality_score', 0):.0%}  "
                f"rr={s.get('rr_tp1', 0):.1f}{fallback_flag}"
            )
            bucket = by_regime.setdefault(regime, {"wins": 0, "losses": 0, "pnl": 0.0})
            if s.get("outcome") == "win":
                bucket["wins"] += 1
            elif s.get("outcome") == "loss":
                bucket["losses"] += 1
            bucket["pnl"] += float(s.get("pnl_dollars", 0) or 0)

        sess_lines = [
            f"  {r.get('session')}: {r.get('wins',0)}W/{r.get('losses',0)}L "
            f"total=${r.get('total_pnl',0):+.2f}"
            for r in by_sess
        ]
        level_lines = [
            f"  {r.get('key_level_type')}: {r.get('wins',0)}W/{r.get('losses',0)}L "
            f"total=${r.get('total_pnl',0):+.2f}"
            for r in by_level
        ]
        regime_lines = [
            f"  {regime}: {b['wins']}W/{b['losses']}L total=${b['pnl']:+.2f}"
            for regime, b in sorted(by_regime.items())
        ]

        # TG provider outcome stats (success = reached TP1)
        tg_source_stats: dict = {}
        for row in tg_rows:
            src = row.get("source_name") or "unknown"
            if src not in tg_source_stats:
                tg_source_stats[src] = {"total": 0, "wins": 0}
            tg_source_stats[src]["total"] += 1
            tg_source_stats[src]["wins"]  += int(row.get("success", 0))
        tg_lines = [
            f"  {src}: {d['wins']}/{d['total']} TP1-success"
            for src, d in sorted(tg_source_stats.items())
        ]

        system_prompt = (
            "You are an algorithmic trading parameter optimizer for a XAUUSD signal generator. "
            "Analyse the provided trade history and respond ONLY with a single minified JSON object "
            "matching this exact schema — no other text:\n"
            '{"adjustments":[{"param":"<name>","new_value":<number>,"regime":"<trending|ranging|neutral|null>",'
            '"reason":"<one sentence>"}],'
            '"summary":"<2-3 sentence analysis of what drove wins vs losses>"}\n\n'
            "Available parameters you may adjust (only include a param if genuinely supported by data):\n"
            + ap.catalogue_for_prompt() +
            "\n\nCurrent per-regime learned values (params marked 'learnable per-regime' above):\n"
            + ap.regime_catalogue_for_prompt() +
            "\n\nRules:\n"
            "- Only recommend changes supported by clear evidence in the data.\n"
            "- If sample < 5 trades or performance is acceptable (win rate >= 55%), return empty adjustments.\n"
            "- Never set a value outside the stated range — it will be clamped anyway.\n"
            "- allow_asian and allow_counter_bias must be exactly 0 or 1.\n"
            "- Prefer small incremental changes (±0.05 to ±0.15) over large jumps.\n"
            "- For params marked 'learnable per-regime': if losses are concentrated in ONE regime "
            "(see regime breakdown below), set \"regime\" to that regime so the fix only applies there "
            "and does not affect performance in other regimes. Set \"regime\" to null (or omit it) for "
            "a genuinely global adjustment, or for any param not marked per-regime."
        )

        user_prompt_parts = [
            f"Virtual account balance: ${balance:.2f} (started $1,000.00)",
            f"Overall stats: {stats['wins']}W / {stats['losses']}L / {stats['be']}BE  "
            f"win_rate={stats['win_rate']}%  avg_pnl=${stats['avg_pnl_dollars']:+.2f}",
            "",
            f"Last {len(recent)} trades:",
            *trade_lines,
            "",
            "Performance by market regime (this batch):",
            *regime_lines,
            "",
            "Performance by session:",
            *sess_lines,
            "",
            "Performance by level type:",
            *level_lines,
        ]
        if tg_lines:
            user_prompt_parts += ["", "Telegram provider TP1-success rates (last 7 days):"] + tg_lines
        user_prompt = "\n".join(user_prompt_parts)

        try:
            import json as _json

            raw = await ai_provider.complete(cfg, system_prompt, user_prompt, max_tokens=500, timeout=25)
            # Strip markdown code fences — the model sometimes adds them despite instructions.
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:])
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            data = _json.loads(raw)

            summary     = data.get("summary", "")
            adjustments = data.get("adjustments", [])
            applied     = []

            for adj in adjustments:
                param  = adj.get("param", "")
                value  = adj.get("new_value")
                reason = adj.get("reason", "")
                regime_tag = adj.get("regime") or None
                if param and value is not None:
                    new_v = ap.apply_adjustment(param, float(value), reason, regime=regime_tag)
                    if new_v is not None:
                        tag = f"[{regime_tag}]" if regime_tag else ""
                        applied.append(f"{param}{tag}→{new_v:.4g}")

            applied_str = (", ".join(applied)) if applied else "no changes"
            log_msg = f"Batch analysis ({len(recent)} trades): {applied_str}. {summary}"

            tdb.log_analysis({
                "ts":              time.time(),
                "result":          f"batch_analysis:{len(recent)}_trades",
                "claude_decision": log_msg,
            })
            _log.info("[TestSignal] %s", log_msg[:200])

        except Exception as e:
            # Log failures too (not just successes) so a silently broken batch loop
            # (bad JSON, timeout, API error) is visible in the analysis log instead
            # of vanishing without a trace.
            err_msg = f"Batch analysis failed ({len(recent)} trades): {e}"
            tdb.log_analysis({
                "ts":              time.time(),
                "result":          "batch_analysis_failed",
                "claude_decision": err_msg[:300],
            })
            _log.warning("[TestSignal] %s", err_msg)


# ── Module-level singleton ────────────────────────────────────────────────────

_instance: Optional[TestSignalEngine] = None


def init(bridge: "MT5BridgeClient") -> TestSignalEngine:
    global _instance
    from forex_trader.config import USER_DATA_DIR
    _setup_log(USER_DATA_DIR / "data")

    db_path = str(USER_DATA_DIR / "data" / "test_signal.db")
    tdb.init(db_path)
    _log.info("Test signal DB: %s", db_path)

    ml.init(USER_DATA_DIR / "data")

    _instance = TestSignalEngine(bridge)
    return _instance


def get_instance() -> Optional[TestSignalEngine]:
    return _instance
