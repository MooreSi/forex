# 020 — Extract GD Copy research sweep

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_gd_copy_research.py` as `gd_copy_research_sweep(engine,
now=None, research_runner=None)` -- taking `engine` explicitly (forwarded
to the pipeline unchanged, exactly as the original passed `self`), `now`
injectable for determinism (defaults to the real
`datetime.now(ZoneInfo("Europe/London"))`), and `research_runner`
injectable (defaults to the real `telegram_research.run_nightly_research`).

The loop's own `try`/`except asyncio.CancelledError: break` /
`except Exception` stays in `engine.py`'s thin wrapper -- the extracted
function raises rather than swallowing, matching every other pack in this
cluster where per-cycle error handling stays at the loop-shell level
(surface test `test_pipeline_exception_propagates` covers this
intentional, documented difference from 010's still-swallowing
characterization of the original method).

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- `now`/`research_runner`
  passed as explicit parameters instead of mocking `engine.datetime`; the
  exception-swallowing test is replaced with a propagation test per the
  decision above.

## What to do

1. Confirm 010's suite is green.
2. Create `core_gd_copy_research.py`, porting the per-cycle body.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_gd_copy_research.py` (41 lines) with
`gd_copy_research_sweep`. 7 tests ported into
`tests/core/test_gd_copy_research_surface.py` -- one assertion changed
(exception propagates instead of being swallowed, per the decision to leave
cycle-level error handling in engine.py's still-untouched wrapper), the
rest unchanged. All 7 pass.

Full `tests/core/` suite: 1084 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted in
`core-max-tp-hit-migration`'s 020 doc -- confirmed still present and
unchanged in count). Full repo `tests/` suite: 1417 passed, 4 failed, same
failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- this pack's function never calls an order-placing
collaborator.
