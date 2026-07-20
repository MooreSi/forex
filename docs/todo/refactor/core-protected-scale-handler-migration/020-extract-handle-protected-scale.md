# 020 — Extract _handle_protected_scale

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- identical call shape to the original; this
pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_protected_scale.py` as a single plain async function taking `bridge`,
a `TPCache` (pack 5), and `close_full_after_tps` (optional injected callable) explicitly.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_protected_scale.py`, porting the function 1:1 (drop `self`, take
   collaborators explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_protected_scale.py` (143 lines) -- 1:1 port, no logic
changes, `bridge`/`tp_cache`/`close_full_after_tps` taken explicitly. Learned from pack 19's
self-caught bug: kept the `break` after the `auto_closed` check unconditional (only the
callback invocation itself is gated by `mt5_ticket and close_full_after_tps`), matching the
original's structure exactly this time -- no equivalent bug this pack. Added
`tests/core/test_handle_protected_scale_surface.py` (8 tests, 010's exact assertions
re-pointed at the new function). Full `tests/core/` suite: 569/569 green (561 from packs 1-20 +
8 from this pack). Repo-wide: 900/902 green -- same 2 pre-existing `pytest-asyncio`-missing
failures from earlier packs, unrelated. `engine.py` untouched -- new function not yet wired
back in. No real or demo MT5 order was placed, closed, or modified at any point in this pack.
