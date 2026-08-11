# 010 — Characterize _run_tp_ladder (+ 3 wrappers)

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs.

## Tests first (TDD)

- `tests/core/test_run_tp_ladder_characterization.py`:
  - No TP hit -> no-op.
  - TP1 hit (Signal Climber, `be_at_pos=0`): closes the TP-count-appropriate percentage,
    moves SL to breakeven immediately.
  - TP1 hit (GD VIP Runner/Adaptive Runner-style, `be_at_pos=1`): closes its own percentage,
    SL stays at its wider entry level (not moved to BE yet).
  - TP2 hit after TP1 (`be_at_pos=1`): NOW moves SL to breakeven.
  - TP3 hit after TP1+TP2: SL trails to TP2's price, not TP1's or entry.
  - TPs are ordered — a tick that hasn't cleared the next un-triggered TP stops the walk there,
    even if a later TP number happens to be technically in range (shouldn't be reachable in
    practice, but the `break`-not-`continue` behavior is worth locking down).
  - A TP on the wrong side of entry is excluded from the ladder entirely (same "correct side"
    filter as the pre-trade filters).
  - The close-schedule table is selected by TP COUNT (`n`), not by which TP number is
    currently hit — a 3-TP signal uses the 3-entry row of the table for every level.
  - The last TP in the ladder always closes 100% of remaining, regardless of its table
    percentage.
  - A gap in the TP sequence (e.g. tp2 NULL, tp3 populated) doesn't truncate the ladder — tp3
    is still reachable.
  - Bridge partial-close rejection at one TP: skips that TP (continues the loop, doesn't abort
    the whole ladder walk).
  - No `mt5_ticket`: skips the bridge entirely, still records partial closes and SL trail in
    the DB.
  - All three wrapper handlers (`_handle_signal_climber`/`_handle_gd_vip_runner`/
    `_handle_adaptive_runner`) actually pass the right table + `be_at_pos` through to
    `_run_tp_ladder` — verified by observing the resulting behavior differs correctly between
    them for the same tick sequence.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._run_tp_ladder`/`_handle_signal_climber`/`_handle_gd_vip_runner`/
   `_handle_adaptive_runner` via `SimulationEngine.__new__(SimulationEngine)` with
   `_tp_cache = {}`, `_tp_wait_log_ts = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

11 tests written in `tests/core/test_run_tp_ladder_characterization.py`. No `engine.py` bugs
found; one test-design mistake caught and fixed (my own wrong expectation, not the production
code): when the last TP fully empties an MT5-backed position, the function schedules
`_close_full_after_tps` (fire-and-forget) and **returns immediately** — it never reaches the
SL-trail block below that point, so no `modify_order` call happens on the closing TP itself
(there's nothing left to protect). A mid-ladder TP, by contrast, DOES trail SL.

Confirmed a single tick that clears multiple un-triggered TP levels at once (e.g. a price gap)
processes ALL of them sequentially within the same function call — the `triggered` set is a
local variable seeded from the persisted cache and mutated in-loop, so TP2 correctly sees TP1
as already-handled within the same call even though nothing was written back to the cache yet.
Confirmed the close-schedule table is selected once by TP COUNT (not per-TP-number), a TP on
the wrong side of entry is excluded from the ladder entirely (changing which row of the table
applies), and a gap in the TP sequence doesn't truncate the walk. Confirmed all three wrapper
handlers correctly pass through their own table + `be_at_pos` — Signal Climber moves SL to BE
at TP1 with a front-loaded table, GD VIP Runner delays BE to TP2 with a back-loaded table, and
Adaptive Runner uses the back-loaded table but moves BE at TP1.
