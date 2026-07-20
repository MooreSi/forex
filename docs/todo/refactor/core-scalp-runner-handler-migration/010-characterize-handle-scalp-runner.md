# 010 — Characterize _handle_scalp_runner

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs (most recently
`core-conservative-handler-migration`).

## Tests first (TDD)

- `tests/core/test_handle_scalp_runner_characterization.py`:
  - No `tp1` on the trade -> no-op.
  - TP1 not yet cleared -> no-op.
  - TP1 cleared: closes 50% of `lot_size` via the bridge, does NOT move SL (unlike
    Conservative), returns without touching phase 2/3 logic in the same call.
  - Bridge rejects the TP1 partial close: sends a failure Telegram alert, returns
    without calling `partial_close_trade` at all.
  - `auto_closed` result from TP1's close: schedules `_close_full_after_tps` and
    returns before any SL-move step.
  - TP1 already triggered, TP2 not cleared -> no-op (waiting for TP2).
  - TP2 cleared: moves SL to breakeven, does NOT partial-close again, returns
    before phase-3 trail logic.
  - TP2 already triggered (phase 3): trails the remaining 50% with the fixed 3pt
    distance, floored at breakeven.
  - Phase 3, price retreats -> SL doesn't move backward.
  - No `mt5_ticket`: DB still updates, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_scalp_runner` via `SimulationEngine.__new__(SimulationEngine)`
   with `_tp_cache = {}`, `_tp_wait_log_ts = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

10 tests written in `tests/core/test_handle_scalp_runner_characterization.py`. No
`engine.py` bugs found; same non-obvious characterization finding as pack 22
(`core-conservative-handler-migration`) recurred here: `partial_close_trade`
(pack 9) independently moves SL to breakeven whenever `reason=="TP1"` and
`move_sl_to_be_after_tp1` is on (the default) — this fires even in
`_handle_scalp_runner`'s own phase 1, which has NO SL-move logic of its own at
that point (unlike Conservative, Scalp Runner deliberately waits until TP2 to
move SL). So the DB row's `stop_loss` ends up at breakeven right after TP1,
one full phase earlier than the handler's own code would suggest —
`bridge.modify_order` still correctly never fires in phase 1 (nothing in this
handler calls it there), but the DB-level SL already reflects breakeven by the
time phase 2 checks `current_sl != null and should_move`. Confirmed this
doesn't break phase 2's own BE-move logic: phase 2 recomputes
`should_move = entry_price > current_sl` (or `<` for SELL), which is now False
once SL is already at breakeven, so phase 2 correctly skips re-alerting/
re-moving — a case not explicitly tested here since it falls out of the
existing `test_tp2_cleared_moves_sl_to_be_no_partial_close` test's premise
(that test builds its trade row directly at `stop_loss=2390.0`, i.e. as if
`partial_close_trade`'s side effect from a prior TP1 call weren't yet
reflected in this particular fixture — a simplification consistent with every
prior pack's TP-boundary test setup, which sets DB state directly rather than
chaining a real TP1 call into a real TP2 call).
