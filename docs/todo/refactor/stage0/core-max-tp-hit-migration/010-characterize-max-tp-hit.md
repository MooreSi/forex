# 010 — Characterize max TP hit checker + backfill

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none -- read-only candle fetches and DB writes to
`max_tp_hit`, no order placed/modified/closed.

## Decision

Both target methods are async loops with no separate "sweep body" method to
call in isolation (unlike `_tp_safety_net_sweep`, which already existed as
its own method). `_max_tp_checker_loop` is characterized by calling the
original bound method directly with `asyncio.sleep` patched to flip
`self._monitor_running = False` on its *second* call -- letting the startup
delay's `sleep(90)` pass through unaffected and the loop run exactly one
cycle before exiting via its own tail `sleep(300)`. `_backfill_max_tp_hit_corrected`
has no `while` wrapper, so it's called directly with `asyncio.sleep` patched
to a no-op.

Every branch pre-traced via throwaway scripts first, given the interacting
DB-filter/candle-fetch/ledger-push gates.

## Tests first (TDD)

- `tests/core/test_max_tp_hit_characterization.py`:
  - `_max_tp_checker_loop`, missing/zero `open_time` -> `max_tp_hit` saved as
    `"none"` directly, no candle fetch, no ledger push.
  - Normal BUY trade -> `sig_tpN` preferred over `tpN` when both set; highest
    level whose price the extreme reached is saved; ledger push includes the
    computed `max_tp_hit` and a `pnl_dollars`/`outcome` (`win`/`loss`/`be`,
    thresholded at ±0.5) derived from `net_pnl`.
  - No candles returned -> skipped entirely (no save, no push, will retry
    next cycle).
  - A per-trade exception (candle fetch raises) doesn't stop the loop from
    processing the remaining pending trades.
  - SL exception aside: a `push_trade_closed` exception is swallowed and
    doesn't prevent the `max_tp_hit` save that already happened.
  - `net_pnl` of exactly `0.0` -> `outcome="be"`; negative -> `"loss"`.
  - `_backfill_max_tp_hit_corrected`: recomputed value equal to the stored
    `max_tp_hit` -> skipped (no save, no ledger push, not counted).
  - Recomputed value different -> saved, ledger pushed, counted.
  - Fetch of `get_trades_with_max_tp_set` raising -> logged, returns cleanly
    (no exception escapes, no trades processed).
  - A per-trade exception doesn't stop the backfill from processing the
    remaining trades.
  - `_tp_level_from_extreme` (module-level pure helper): BUY/SELL threshold
    direction; `None` TP mid-ladder is skipped, not treated as a stop (a gap
    must not hide levels beyond it); no level reached -> `"none"`.

## What to do

1. Write the test file using a fake bridge (`get_candles_range`), calling
   the two original bound methods via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- this pack's
  functions never call an order-placing collaborator at all.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

14 tests written in `tests/core/test_max_tp_hit_characterization.py`, all
green on the first run against unmodified `engine.py` -- every branch
pre-traced via throwaway scripts first. No `engine.py` bugs found.

Confirmed both `get_trades_pending_max_tp`/`get_trades_with_max_tp_set`
already filter to `close_time > 0` at the SQL level, so the "missing
close_time" defensive branch in both loops is dead code against real data --
not separately tested (would require constructing a row shape the DB
functions themselves can never return).
