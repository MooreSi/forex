# 020 — Extract email scheduler sweep

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none directly; the ORB auto-execute path forwards
to the already-extracted, already-characterized `core_orb_report.orb_auto_execute`.

## Decision

Extract into `core_email_scheduler.py` as `email_scheduler_sweep(bridge,
cfg_obj, is_active_trader_node, uk_now=None, local_now=None)`, split
internally into three private helpers (`_run_orb_section`,
`_run_daily_section`, `_run_weekly_section`) mirroring the original's three
sections one-to-one -- not separately exported, since nothing outside this
sweep calls them independently. Reuses `core_orb_report.build_orb_report`/
`orb_auto_execute` and `core_mt5_performance.compute_mt5_performance` as
real, imported collaborators (both already extracted in earlier packs)
rather than re-deriving them.

The two early "skip the rest of this cycle" `continue`s in the original
loop (no provider configured; send-time mismatch) become early `return`s in
the extracted function -- the loop's own trailing `sleep(60)` in
`engine.py`'s still-untouched wrapper covers what the `continue`s used to
reach for free either way.

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- `uk_now`/`local_now`/
  `is_active_trader_node` passed as explicit parameters instead of mocking
  `engine.datetime`/`SimulationEngine._is_active_trader_node`; collaborator
  patches target the names imported into `core_email_scheduler` rather than
  their origin modules.

## What to do

1. Confirm 010's suite is green.
2. Create `core_email_scheduler.py`, porting the per-cycle body split into
   the three section helpers above.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point --
  `orb_auto_execute` (the only path that could) is always faked.

## Notes

Created `forex_trader/core/core_email_scheduler.py` (191 lines). 9 tests
ported into `tests/core/test_email_scheduler_surface.py` -- import/patch-
target changes and explicit `now`/node-flag parameters only, zero assertion
changes. All 9 pass.

Full `tests/core/` suite: 1102 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted in every pack since
`core-max-tp-hit-migration`'s 020 doc -- confirmed still present and
unchanged in count). Full repo `tests/` suite: 1435 passed, 4 failed, same
failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.
