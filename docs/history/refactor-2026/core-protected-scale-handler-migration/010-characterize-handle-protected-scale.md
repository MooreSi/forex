# 010 — Characterize _handle_protected_scale

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs.

## Tests first (TDD)

- `tests/core/test_handle_protected_scale_characterization.py`:
  - TP1 cleared: marked `TP1_SKIPPED`, no partial close, no SL move, no `modify_order` call.
  - TP1 already marked -> not re-processed on a second call.
  - TP2 cleared: marked `TP2_BE_LOCKED`, SL moves to breakeven, `modify_order` called -- still
    no partial close for TP2 itself.
  - TP2 already at/past breakeven -> no `modify_order` call (guarded by `should_update`).
  - TP3 cleared: closes a flat 20% of `lot_size`.
  - TP3 not yet cleared but TP4 nominally in range -> the `break`-on-first-miss ordering means
    TP4 is never reached in that tick (TPs are ordered).
  - Bridge partial-close rejection at TP3: `continue`s the loop (TP4/5 still attempted if also
    cleared).
  - `auto_closed` result at any of TP3-5: `break`s out of the loop for the rest of this call.
  - No `mt5_ticket`: DB still updates, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_protected_scale` via `SimulationEngine.__new__(SimulationEngine)`
   with `_tp_cache = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

8 tests written in `tests/core/test_handle_protected_scale_characterization.py`, all green
against unmodified `engine.py` on first run. No bugs found. Confirmed TP1 and TP2 are pure
bookkeeping/protection steps (no partial close for either), TP3-5 each close a flat 20%
regardless of position in the ladder (unlike Scale Out's tapering schedule or the TP-ladder
handlers' count-indexed tables), and the `break`-on-first-miss ordering means a later TP is
never even inspected if an earlier one hasn't cleared yet in the same tick.
