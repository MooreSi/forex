# 020 — Extract _handle_scale_out

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- identical call shape to the original; this
pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_scale_out.py` as a single plain async function taking `bridge`, a
`TPCache` (pack 5), and `scale_out_last_fail: dict` explicitly. `close_full_after_tps` taken as
an optional injected async callable (default no-op) -- see README.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_scale_out.py`, porting the function 1:1 (drop `self`, take `bridge`/
   `tp_cache`/`scale_out_last_fail` explicitly, `close_full_after_tps` as an optional callable).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_scale_out.py` (121 lines) -- 1:1 port, no logic changes,
`bridge`/`tp_cache`/`scale_out_last_fail` taken explicitly, `close_full_after_tps` as an
optional injected callable (default `None`, silently skipped exactly like the original's
`asyncio.create_task` fire-and-forget would be if there were nothing to schedule). Added
`tests/core/test_handle_scale_out_surface.py` (9 tests, 010's exact assertions re-pointed at
the new function, plus one new test confirming the injected `close_full_after_tps` callable is
actually invoked on auto-close). No background-task warning noise this time, as expected --
the default `None` means nothing fires when the caller doesn't supply a real implementation.

Full `tests/core/` suite: 501/501 green (492 from packs 1-16 + 9 from this pack). Repo-wide:
832/834 green -- same 2 pre-existing `pytest-asyncio`-missing failures from earlier packs,
unrelated. `engine.py` untouched -- new function not yet wired back in. No real or demo MT5
order was placed, closed, or modified at any point in this pack.
