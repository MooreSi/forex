# 020 — Extract bridge watchdog check

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_bridge_watchdog.py` as `bridge_watchdog_check(bridge,
state, bridge_inhibit_reconnect, start_bridge_process, now_monotonic=None)`,
returning the number of seconds to sleep before the next check
(`CHECK_INTERVAL`/`STARTUP_WAIT`, both exported as module constants
alongside `RESTART_COOLDOWN`/`CONSECUTIVE_FAIL_THRESHOLD`). `state` is
mutated in place; callers own its lifetime across calls (the `while`/
`sleep(180)` startup delay/`sleep(<returned value>)` shell stays in
`engine.py`).

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- called once per cycle in
  a small loop instead of driving the original's own `while`, `state`
  seeded explicitly instead of relying on the method's local-variable
  defaults, `start_bridge_process` no longer needs the `self` parameter
  (it's a plain injected callable here, not a class-patched method). One
  additional test (`test_cooldown_allows_second_restart_when_now_monotonic_advances`)
  exercises the cooldown-elapsed restart path directly via `now_monotonic`,
  which 010 could only exercise indirectly by waiting out real wall-clock
  time (not attempted there).

## What to do

1. Confirm 010's suite is green.
2. Create `core_bridge_watchdog.py`, porting the single-cycle body,
   returning the next-sleep duration instead of sleeping internally.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_bridge_watchdog.py` (107 lines). 14 tests
written in `tests/core/test_bridge_watchdog_surface.py` -- 13 ported from
010 (state/callable passed explicitly instead of mocking the class, `waits`
list asserted instead of a mocked `asyncio.sleep`'s call log), plus 1 new
test directly exercising the cooldown-elapsed second-restart path via
`now_monotonic` (010 could only prove the cooldown-*not*-elapsed path,
since real wall-clock time between mocked-instant test iterations is
always ~0ms). All 14 pass.

Full `tests/core/` suite: 1129 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1462
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.
