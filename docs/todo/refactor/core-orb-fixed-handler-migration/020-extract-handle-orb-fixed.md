# 020 — Extract _handle_orb_fixed

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** closes an open position via `bridge.partial_close` -- identical call
shape to the original; this pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_orb_fixed.py` as a single plain async function taking `bridge` and a
`TPCache` (pack 5) explicitly. Reuses `core_tp_trigger_tracking.check_tp_hits`/
`get_remaining_lots` (pack 5), `core_partial_close.partial_close_trade` (pack 9).

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_orb_fixed.py`, porting the function 1:1 (drop `self`, take `bridge`/
   `tp_cache` explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_orb_fixed.py` (67 lines) -- 1:1 port, no logic changes,
`bridge`/`tp_cache` taken explicitly. Added `tests/core/test_handle_orb_fixed_surface.py` (5
tests, 010's exact assertions re-pointed at the new function). Full `tests/core/` suite:
484/484 green (479 from packs 1-15 + 5 from this pack). Repo-wide: 815/817 green -- same 2
pre-existing `pytest-asyncio`-missing failures from earlier packs, unrelated. `engine.py`
untouched -- new function not yet wired back in.

No real or demo MT5 order was placed, closed, or modified at any point in this pack -- the one
`bridge.partial_close` call went to a plain in-memory fake, call log asserted directly.
