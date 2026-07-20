# 010 — Characterize _handle_conservative

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs.

## Tests first (TDD)

- `tests/core/test_handle_conservative_characterization.py`:
  - No `tp1` on the trade -> no-op.
  - TP1 not yet cleared -> no-op.
  - TP1 cleared: closes 80% of `lot_size` via the bridge, moves SL to breakeven, returns
    without touching the trailing-phase logic in the same call.
  - Bridge rejects the TP1 partial close: sends a failure Telegram alert, returns without
    calling `partial_close_trade` at all.
  - `auto_closed` result from TP1's close (e.g. tiny remaining lot rounds the 80% up to
    everything): schedules `close_full_after_tps` and returns before the BE-SL-move step.
  - TP1 already triggered (phase 2): trails the remaining 20% with the fixed 3pt distance,
    floored at breakeven -- never re-attempts the TP1 close/80% logic.
  - Phase 2, price retreats -> SL doesn't move backward.
  - No `mt5_ticket`: DB still updates in both phases, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_conservative` via `SimulationEngine.__new__(SimulationEngine)`
   with `_tp_cache = {}`, `_tp_wait_log_ts = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

8 tests written in `tests/core/test_handle_conservative_characterization.py`. No `engine.py`
bugs found; one real, non-obvious characterization discovery caught by a genuine test failure
(not by inspection): **`partial_close_trade` (pack 9) has its own independent "move SL to
breakeven" logic** baked in whenever `reason=="TP1"` and `move_sl_to_be_after_tp1` is on (the
default) — it writes `stop_loss=entry_price` directly as part of computing its own return
value, *before* `_handle_conservative` ever checks `auto_closed`. This means the DB row's SL
ends up at breakeven even in the auto-closed case where `_handle_conservative`'s OWN "move SL
to BE" block never runs (it returns immediately after scheduling `close_full_after_tps`) —
`bridge.modify_order` correctly never fires in that case (nothing left to modify), but the
DB-level SL still moves via the other mechanism. Not a bug, and not something either pack
should fix (`partial_close_trade`'s behavior was already characterized correctly in pack 9;
this pack's handler is simply layering its own broker-sync + Telegram-alert logic on top of an
SL move that, for `reason=="TP1"`, has already happened one level down). Worth flagging for
whoever eventually wires strategies back into `engine.py`, since it means
`_handle_conservative`'s own BE-move block is partially redundant for the DB write specifically
(not for the broker sync or alert, which it alone provides).
