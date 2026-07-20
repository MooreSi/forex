# 020 — Extract signal CRUD

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract as plain functions (none of the four use `self`) into `core_signals.py`, calling
`db_module` directly -- same shape as pack 1, no parallel repo.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_signals.py`, porting each function 1:1 (drop `self`, no logic changes).
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as pack 1 and the engine packs.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_signals.py` (91 lines, well under the 800-line ceiling) — 1:1
port of `create_signal`/`get_signals`/`activate_signal`/`cancel_signal`, no logic changes.
Added `tests/core/test_signal_crud_surface.py` (12 tests, 010's exact assertions re-pointed at
the new module functions). Full `tests/core/` suite: 106/106 green (82 from pack 1 + 24 from
this pack). Repo-wide: 437/439 green — the same 2 pre-existing `pytest-asyncio`-missing
failures from pack 1 (`tests/test_signal/test_engine_characterization.py`), unrelated to this
pack. `engine.py` untouched — new functions not yet wired back in.
