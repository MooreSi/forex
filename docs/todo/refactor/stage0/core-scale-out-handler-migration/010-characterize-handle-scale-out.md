# 010 — Characterize _handle_scale_out

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs, extended with `partial_close` call-log capture
(already have `modify_order` from pack 15's fake).

## Tests first (TDD)

- `tests/core/test_handle_scale_out_characterization.py`:
  - No TP hit -> no-op.
  - TP1 hit: closes 40% of `lot_size` (not remaining) via the bridge; moves SL to breakeven
    (`sl_moved_to_be`) and calls `bridge.modify_order` for the SL move, since this is the
    first TP1 hit.
  - TP1 hit again with `sl_moved_to_be` already set -> partial close still fires, but no
    second SL-move / `modify_order` SL call.
  - TP2/TP3/TP4 hit: closes 30/20/10% of `lot_size` respectively (clamped to whatever's
    actually remaining).
  - The LAST defined TP (whichever number) always closes 100% of remaining, not its tiered
    percentage.
  - A TP5+ hit (beyond the tiered table) with lots still remaining closes 100% of remaining.
  - Bridge partial-close rejection: records a retry-cooldown timestamp in
    `scale_out_last_fail` for that (trade_id, tp_num) and does NOT call `partial_close_trade`;
    a second attempt within 30s of the failure is skipped entirely (no bridge call at all); a
    successful retry after the cooldown clears the failure entry.
  - No `mt5_ticket` (pure sim trade): skips the bridge partial-close call entirely, still
    records the partial close at the signal's own TP price.
  - `auto_closed` result from `partial_close_trade` (remaining hits zero) with an `mt5_ticket`
    schedules `_close_full_after_tps` (captured via the injected callable in 020; 010
    characterizes only that the original fires `asyncio.create_task` without raising).

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_scale_out` via `SimulationEngine.__new__(SimulationEngine)` with
   `_tp_cache = {}`, `_scale_out_last_fail = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

8 tests written in `tests/core/test_handle_scale_out_characterization.py`. No `engine.py` bugs
found; two test-design corrections needed along the way (both my own test setup, not the
production code): a TP2/TP3/TP4 scenario needs the EARLIER TP(s) marked as already-triggered
via a real `vantage_partial_closes` row (setting `remaining_lots`/`sl_moved_to_be` alone on the
trade row isn't enough — `_check_tp_hits` independently re-derives "already triggered" from the
partial-closes table, so an unrecorded earlier TP gets re-detected as freshly hit in the same
tick and processed first, silently changing which TP the test's assertion was actually
exercising).

Confirmed the last-defined TP always forces a full close of whatever remains, overriding its
own tiered percentage — this is the SAME code path a genuine "TP5+" hit takes (`_SCALE_OUT_PCTS`
only has entries for 1-4, so any TP without a tiered percentage also falls through to closing
100%). `remaining` is re-fetched fresh from the DB on every iteration of the hits loop, so a
single tick that (in a contrived setup) clears multiple un-recorded TP levels at once only ever
acts on the first one — later iterations see `remaining<=0` and skip.

`_close_full_after_tps` fires via `asyncio.create_task` (fire-and-forget, unawaited) whenever a
partial close empties the position — confirmed via an "Task exception was never retrieved"
asyncio warning when the fake bridge lacked the unrelated methods that out-of-scope call chain
needs (`get_position_history` etc.). Harmless for characterization (the exception surfaces
asynchronously, after the test's own synchronous assertions already completed) and expected
to disappear entirely in 020's surface tests once the callable is properly injected as an
optional no-op.
