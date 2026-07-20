# 010 — Characterize _process_instant_entry

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** places a genuine MT5 market order via `open_trade`
(already-extracted, pack 11) and later syncs SL/TP via `bridge.modify_order` --
`open_trade` itself is faked (mocked) in every test here, same treatment as
`dpm_engine.compute_adaptive_params` in the DPM handler pack; its own real
behavior was already characterized in its own extraction pack.

## Decision

`open_trade` faked via `unittest.mock.patch.object(SimulationEngine, "open_trade",
new=mock.AsyncMock(...))`, asserting on its call kwargs (`lot_size`, `stop_loss`,
etc.) rather than its real effects. `_get_trading_balance`/`get_open_trades`/
`get_tick` also faked the same way (already-extracted, out of scope for this pack).
Every numeric branch was traced against unmodified `engine.py` first via
throwaway scripts, given the three interacting lot-sizing paths.

## Tests first (TDD)

- `tests/core/test_instant_entry_characterization.py`:
  - Stale message (timestamp > 4 min old) -> recorded `instant_historical`, no
    signal/trade opened, function returns before any gating checks.
  - No timestamp at all -> treated as stale (same as above) -- a genuine live
    message always carries one.
  - Not stale, `auto_execute=False` -> recorded `instant_pending`, no signal/trade.
  - Session not allowed (`is_session_allowed` returns False) -> no signal/trade.
  - No live tick available -> no signal/trade.
  - Spread wider than `max_allowed_spread_points` -> no signal/trade.
  - `max_open_trades` already reached -> no signal/trade.
  - Default risk-pct-based sizing (Risk Governor off, no fixed lot): ATR
    unavailable (no dpm_candles) -> 12pt provisional SL distance (the
    ATR-unavailable default, clamped 8-25), lot floored to 0.01 (a $5 risk
    budget on a 12pt stop rounds to 0.0, then clamped up).
  - Risk Governor on, no fixed lot, default risk settings: the risk-correct
    lot size rounds below 0.01 -> the whole entry is skipped, `open_trade`
    never called.
  - Risk Governor on, no fixed lot, generous risk_per_trade_pct but a tight
    max_risk_per_trade_pct cap: the cap (not the raw risk-based size) binds.
  - Risk Governor on, fixed lot set: uses the fixed lot directly, same
    12pt-default SL distance logic as the risk-pct path.
  - Risk Governor off, fixed lot set: SL distance instead derived from a
    $150-max-loss cap (clamped 8-25pt) -- a materially different distance
    than the Governor-on fixed-lot case.
  - Channel strategy override `"auto"` -> uses the last Claude recommendation.
  - Explicit channel strategy override -> used directly.
  - `"high risk"` in the message text -> forces Conservative regardless of any
    other override.
  - Conservative strategy post-fill: SL/TP1 set to fixed points from the
    actual fill price (not the provisional SL), broker-side `modify_order`
    synced, TP2-8 cleared.
  - Conservative Trial post-fill: SL + all 6 TPs set to a fixed six-tier
    ladder from the actual fill price.
  - `open_trade` raising any exception: the provisional `vantage_signals` row
    is deleted and the originating `vantage_tg_signals` row is marked
    `instant_failed` -- verified for both a generic exception and a
    circuit-breaker/trading-paused message (same cleanup either way; this
    pack does not assert on log level, only on DB state).

## What to do

1. Write the test file using a fake bridge (`modify_order`) and mocked
   `SimulationEngine.open_trade`/`_get_trading_balance`/`get_open_trades`/
   `get_tick`, calling `SimulationEngine._process_instant_entry` via
   `SimulationEngine.__new__(SimulationEngine)` with `_dpm_candles = []`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — `open_trade` is
  mocked in every test, never given a real bridge to act through.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

19 tests written in `tests/core/test_instant_entry_characterization.py`, all
green against unmodified `engine.py`. No `engine.py` bugs found. Every
numeric branch (lot sizes, SL distances, TP ladders) was traced against
unmodified `engine.py` via throwaway scripts before writing final
assertions, given the three interacting lot-sizing paths -- this is the
most branch-heavy single function characterized in the whole migration
series so far, and the pre-tracing avoided significant iteration churn.

Notable findings, all confirmed as intentional behavior (not bugs):

- With the app's own *default* risk settings (`risk_per_trade_pct=0.5`,
  no fixed lot, Risk Governor OFF), the ATR-unavailable 12pt default stop
  distance produces a $5 risk budget that rounds to a 0.0-lot request,
  which then gets clamped back up to the 0.01 minimum -- so the "default"
  path always trades the minimum lot in a fresh install with no candle
  history yet.
- The *same* default settings but with Risk Governor ON instead skip the
  entry entirely rather than clamping up, since the Governor path has no
  0.01 floor -- a materially different outcome for what looks like a
  similar risk config, purely from which of the two sizing branches is active.
- Governor-on-fixed-lot and Governor-off-fixed-lot compute *different* SL
  distances for the identical lot size (12pt ATR-default vs. a 25pt
  $150-max-loss-cap distance respectively) -- confirmed via a dedicated
  pair of tests with the same 0.05 lot.
- `open_trade`'s exception-handling cleanup (deleting the provisional
  signal, marking the tg_signal `instant_failed`) is identical regardless
  of whether the exception message mentions "circuit breaker"/"trading
  paused" -- the original code only special-cases that for log *level*
  (info vs error), which this pack does not assert on since it isn't
  externally observable behavior.
