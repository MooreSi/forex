# 020 — Extract partial close

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none — no bridge call in this method

## Decision

Extract into `core_partial_close.py` as a single plain async function, calling
`core_fees_sizing.pnl()` (pack 1) instead of `self.pnl()`. No collaborator parameter needed —
the method only touches `db_module`.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_partial_close.py`, porting the function 1:1 (drop `self`).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_partial_close.py` (78 lines) -- 1:1 port, no logic changes,
calling pack 1's `core_fees_sizing.pnl()` instead of `self.pnl()`. No collaborator parameter
needed (no bridge involved). Added `tests/core/test_partial_close_surface.py` (10 tests, 010's
exact assertions re-pointed at the new function). Full `tests/core/` suite: 264/264 green (254
from packs 1-8 + 10 from this pack). Repo-wide: 595/597 green -- same 2 pre-existing
`pytest-asyncio`-missing failures from earlier packs, unrelated. `engine.py` untouched -- new
function not yet wired back in. No real or demo MT5 order was placed, closed, or modified at
any point in this pack.
