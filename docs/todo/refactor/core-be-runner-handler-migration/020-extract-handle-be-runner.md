# 020 — Extract _handle_be_runner

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` -- identical call
shape to the original; this pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_be_runner.py` as a single plain async function taking `bridge`,
`dpm_candles`, `tp_cache`, `scale_out_last_fail`, and `close_full_after_tps` explicitly (the
last three passed straight through to pack 17's `handle_scale_out` for the ADX-ranging
fallback).

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_be_runner.py`, porting the function 1:1 (drop `self`, take collaborators
   explicitly, call `core_handle_scale_out.handle_scale_out` for the fallback).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_be_runner.py` (97 lines) -- 1:1 port, no logic changes,
collaborators taken explicitly, reusing pack 17's `handle_scale_out` directly for the
ADX-ranging fallback. Added `tests/core/test_handle_be_runner_surface.py` (8 tests, 010's
exact assertions re-pointed at the new function). Full `tests/core/` suite: 517/517 green (509
from packs 1-17 + 8 from this pack). Repo-wide: 848/850 green -- same 2 pre-existing
`pytest-asyncio`-missing failures from earlier packs, unrelated. `engine.py` untouched -- new
function not yet wired back in. No real or demo MT5 order was placed, closed, or modified at
any point in this pack.
