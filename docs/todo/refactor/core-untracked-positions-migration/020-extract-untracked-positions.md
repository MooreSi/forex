# 020 — Extract untracked MT5 positions

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract into `core_untracked_positions.py` as a single plain async function taking `bridge`
explicitly instead of reading `self._bridge`, and calling
`core_trade_reporting.get_open_trades()` (pack 3) directly instead of `self.get_open_trades()`.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_untracked_positions.py`, porting the function 1:1 (drop `self`, take `bridge`
   as a parameter, call `core_trade_reporting.get_open_trades()` instead of `self.
   get_open_trades()`).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_untracked_positions.py` (36 lines) -- 1:1 port, no logic
changes, `bridge` taken as an explicit parameter and `core_trade_reporting.get_open_trades()`
called directly instead of `self.get_open_trades()`. Added
`tests/core/test_untracked_positions_surface.py` (5 tests, 010's exact assertions re-pointed at
the new function, passing a plain `_FakeBridge` directly instead of setting `self._bridge` on a
`SimulationEngine.__new__()` instance). Full `tests/core/` suite: 210/210 green (205 from packs
1-5 + 5 from this pack). Repo-wide: 541/543 green -- same 2 pre-existing `pytest-asyncio`-
missing failures from earlier packs, unrelated. `engine.py` untouched -- new function not yet
wired back in. This closes out pack 3's explicit deferral.
