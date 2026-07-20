# 020 — Extract TG signals

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract into `core_tg_signals.py` as a single plain function taking `tg_reader` explicitly
(optional, defaulting to `None`) instead of reading `self._tg_reader`.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_tg_signals.py`, porting the function 1:1 (drop `self`, take `tg_reader` as a
   parameter).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_tg_signals.py` (37 lines) -- 1:1 port, no logic changes,
`tg_reader` taken as an explicit optional parameter instead of `self._tg_reader`. Added
`tests/core/test_tg_signals_surface.py` (6 tests, 010's exact assertions re-pointed at the new
function). Full `tests/core/` suite: 222/222 green (216 from packs 1-6 + 6 from this pack).
Repo-wide: 553/555 green -- same 2 pre-existing `pytest-asyncio`-missing failures from earlier
packs, unrelated. `engine.py` untouched -- new function not yet wired back in.
