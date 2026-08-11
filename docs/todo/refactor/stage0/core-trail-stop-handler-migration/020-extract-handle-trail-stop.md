# 020 — Extract _handle_trail_stop

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` -- identical call
shape to the original; this pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_trail_stop.py` as a single plain async function taking `bridge` and a
`TPCache` (pack 5) explicitly.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_trail_stop.py`, porting the function 1:1 (drop `self`, take `bridge`/
   `tp_cache` explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_trail_stop.py` (156 lines) -- 1:1 port, no logic
changes, `bridge`/`tp_cache` taken explicitly. Added `tests/core/test_handle_trail_stop_surface.py`
(7 tests, 010's exact assertions re-pointed at the new function). Full `tests/core/` suite:
553/553 green (546 from packs 1-19 + 7 from this pack). Repo-wide: 884/886 green -- same 2
pre-existing `pytest-asyncio`-missing failures from earlier packs, unrelated. `engine.py`
untouched -- new function not yet wired back in. No real or demo MT5 order was placed, closed,
or modified at any point in this pack.
