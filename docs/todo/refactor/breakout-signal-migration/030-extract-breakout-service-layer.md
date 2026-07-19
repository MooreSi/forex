# 030 — Extract breakout_signal's service layer

**Status:** not started
**Depends on:** 020-migrate-breakout-repo-layer.md
**Real-money surface:** no (no MT5 connection in this task — that's 040, connectivity-only)
**Leverage:** `breakout_signal_repo.py` (020), the gd_copy_signal 040 split as a template

## Problem

`engine.py` (1,686 lines) mixes signal generation (M5 gate), real-time level-cross detection
(velocity loop), TP/SL/partial-close management, live MT5 dispatch, and Claude-based batch
parameter tuning in one file.

## Decision

Same mixin-composition pattern as `gd_copy_signal`'s 040:
- `breakout_signal_service.py` — thin orchestrator: lifecycle, `_cycle_loop`/`_run_cycle`
  (signal generation), `_process_candidate`'s gating logic, `_outcome_loop` (thin routing),
  helpers.
- `breakout_signal_manage.py` — TP/SL/partial-close ladder (`_close_and_learn`, the SL/TP1/TP2/
  TP3 branches inside `_check_outcomes`), `_compute_cost_pts`.
- `breakout_signal_velocity.py` — the 3-second real-time level-cross loop (`_velocity_loop`/
  `_check_velocity_break`) — new relative to gd_copy_signal, gets its own file since it's a
  distinct concern with its own timing/state (`_price_history`, `_velocity_cooldowns`).
- `breakout_signal_live_execute.py` — `_execute_live`, the one real-order-dispatch path.
- `breakout_signal_learn.py` — `_run_batch_analysis` (Claude-based parameter tuning) —
  analogous role to gd_copy_signal's correlation tracking (periodic learning, not per-signal
  orchestration).

## Tests first (TDD)

- 010's engine suite, re-pointed at the new modules (import + fixture changes only).
- `tests/breakout_signal/test_service_surface.py` — same shape as gd_copy_signal's: every
  expected method present and callable, mixins compose correctly, no name collisions.

## What to do

1. Confirm 010's engine suite + 020's repo suite are green (prerequisites).
2. Extract the four mixin files in this order (backend-conventions §7: pure functions first,
   completion/tracking handlers next, transaction-wrapped writes last): `breakout_signal_learn.py`
   → `breakout_signal_velocity.py` → `breakout_signal_manage.py` → `breakout_signal_live_execute.py`.
3. Reduce `engine.py`'s logic into `breakout_signal_service.py`.
4. Re-run 010's suite against the new structure — zero assertion changes.
5. Add and pass `test_service_surface.py`.
6. Do NOT delete `engine.py`/`database.py` — same finding as gd_copy_signal 040 almost
   certainly applies here too (check for external call sites before even considering it).

## Where

- `forex_trader/breakout_signal/breakout_signal_service.py` (new)
- `forex_trader/breakout_signal/breakout_signal_manage.py` (new)
- `forex_trader/breakout_signal/breakout_signal_velocity.py` (new)
- `forex_trader/breakout_signal/breakout_signal_live_execute.py` (new)
- `forex_trader/breakout_signal/breakout_signal_learn.py` (new)
- `tests/breakout_signal/test_service_surface.py` (new)

## Acceptance

- 010's full suite passes against the new structure, zero assertion changes.
- No new file exceeds 800 lines (target well under, per the gd_copy_signal precedent).
- `test_service_surface.py` passes.
- **The killer test:** 010's full-lifecycle test still passes end-to-end through the new stack.

## Notes

Check for external call sites (`grep -rln "breakout_signal\.engine\|breakout_signal import
engine\|breakout_signal\.database\|breakout_signal import database"`) BEFORE assuming
`engine.py`/`database.py` can be deleted — gd_copy_signal's equivalent task found 7 live call
sites that would have broken the app. Don't repeat that assumption without checking first this
time.
