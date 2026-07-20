# 020 — Extract trade reporting

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract as plain functions into `core_trade_reporting.py`, calling `db_module` directly -- same
shape as packs 1-2, no parallel repo. `compute_performance` takes `starting_balance: float` as
an explicit parameter instead of reading `self._cfg`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_trade_reporting.py`, porting each function 1:1 (drop `self`,
   `compute_performance` takes `starting_balance` explicitly).
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as packs 1-2 and the engine packs.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_trade_reporting.py` (172 lines, well under the 800-line
ceiling) -- 1:1 port of `get_open_trades`/`get_all_trades`/`compute_performance`, no logic
changes. `compute_performance` now takes `starting_balance: float` explicitly instead of
reading `self._cfg`. Added `tests/core/test_trade_reporting_surface.py` (14 tests, 010's exact
assertions re-pointed at the new module, `_FakeEngine` replaced with a direct float arg for
`compute_performance`). Full `tests/core/` suite: 134/134 green (120 from packs 1-2 + 14 from
this pack). Repo-wide: 465/467 green -- same 2 pre-existing `pytest-asyncio`-missing failures
from packs 1-2, unrelated. `engine.py` untouched -- new functions not yet wired back in.
