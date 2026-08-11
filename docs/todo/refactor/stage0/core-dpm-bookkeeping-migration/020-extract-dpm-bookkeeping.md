# 020 — Extract DPM bookkeeping

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract into `core_dpm_bookkeeping.py`. `_update_dpm_peak`, `_set_dpm_milestone`,
`_finalize_dpm_record` become plain functions (no `self` needed, same as packs 1-3).
`_load_dpm_calibrated` and `_record_dpm_entry` need cross-call memory that isn't in the DB
(TTL cache, dedup set) -- add one small `DPMCache` class (plain attribute container: `calibrated:
dict`, `loaded_at: float`, `recorded: set[str]`) that callers instantiate and pass in
explicitly. No mixin, no hidden global/instance state -- see README's "What's different".

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, `_FakeEngine` swapped for
  `DPMCache`, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_dpm_bookkeeping.py`: `DPMCache` class, then `load_dpm_calibrated(cache)`,
   `record_dpm_entry(cache, trade, params)`, `update_dpm_peak(trade_id, pnl)`,
   `set_dpm_milestone(trade_id, column)`, `finalize_dpm_record(trade_id, close_price,
   exit_type, final_pnl)` -- 1:1 logic ports.
3. Re-run 010's suite against the new functions -- zero assertion changes (beyond the
   `_FakeEngine` -> `DPMCache` swap).
4. Leave `engine.py` untouched -- same precedent as packs 1-3 and the engine packs.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_dpm_bookkeeping.py` (153 lines, well under the 800-line
ceiling) -- `DPMCache` class plus 1:1 ports of all 5 functions, no logic changes.
`load_dpm_calibrated`/`record_dpm_entry` take a `DPMCache` instance as their first argument
instead of implicit `self` state. Added `tests/core/test_dpm_bookkeeping_surface.py` (14 tests,
010's exact assertions re-pointed at the new module, `_FakeEngine` replaced by a real
`DPMCache()`). Full `tests/core/` suite: 162/162 green (148 from packs 1-3 + 14 from this pack).
Repo-wide: 493/495 green -- same 2 pre-existing `pytest-asyncio`-missing failures from packs
1-3, unrelated. `engine.py` untouched -- new module not yet wired back in.
