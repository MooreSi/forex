# 010 — Characterize MT5 deal history

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no (reads only; `import_mt5_history` writes local DB records only,
never anything to MT5)

## Decision

Same DB approach as prior packs. `self._bridge` is replaced by a small fake test-double
exposing async `get_account()`, `get_deal_history(days)`, `get_positions()` (matching
`MT5BridgeClient`'s real shapes).

## Tests first (TDD)

- `tests/core/test_mt5_history_characterization.py`:
  - `get_total_deposits` — sums `profit` for deals with no `position_id` (balance/deposit ops,
    excludes actual trade deals); caches the result in `app_config` for 1 hour; a second call
    within the hour returns the cached value without calling the bridge again; returns `0.0` on
    a bridge exception.
  - `compute_mt5_performance` — groups deals by `position_id`; computes win rate/profit
    factor/drawdown/run-up from the closed-position P&L (net of estimated fees via
    `_apply_fee`/`_platform_fee_rate`); daily stats from the UK-midnight cutoff; returns `{}` on
    a bridge exception (not a raise).
  - `import_mt5_history` — skips a `position_id` already present as an `mt5_ticket` in
    `vantage_simulated_trades`; skips a position with no open or no close deal; inserts a new
    `vantage_signals` + `vantage_simulated_trades` row for a genuinely new closed position,
    updates the sim balance by the imported profit; derives `exit_reason` from the close deal's
    comment text (SL/TP/MT5_import); returns `{"imported": 0, "skipped": 0, "error": ...}` when
    the bridge returns no deals at all.

## What to do

1. Write the test file against `SimulationEngine`'s real methods, using a fake bridge test-
   double passed as (or set on) the engine. `import_mt5_history` calls `self.pnl(...)`
   internally (pack 1's already-extracted logic, still present unchanged on `engine.py` too) --
   use `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set manually.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from prior packs.

## Notes

11 tests written in `tests/core/test_mt5_history_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. `_FakeBridge` is a plain object (async
`get_account`/`get_deal_history`/`get_positions`) -- no HTTP client, no live MT5 connection ever
constructed. Confirmed `get_total_deposits`' 1-hour cache genuinely skips the bridge call on a
second request within the window (asserted via a call-counter on the fake bridge, not just the
returned value). Confirmed all three exception paths (`get_total_deposits` -> `0.0`,
`compute_mt5_performance` -> `{}`) swallow bridge errors rather than propagating. Confirmed
`import_mt5_history`'s existing-ticket skip, missing-open/close-deal skip, and comment-based
`exit_reason` derivation (SL/TP/MT5_import) all behave as documented, and that the sim balance
update reflects the imported profit exactly once per newly-imported position.
