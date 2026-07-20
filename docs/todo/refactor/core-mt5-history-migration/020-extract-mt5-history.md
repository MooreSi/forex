# 020 — Extract MT5 deal history

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract into three files, each a plain function taking `bridge` explicitly instead of
`self._bridge`:

- `core_total_deposits.py`: `get_total_deposits(bridge)`.
- `core_mt5_performance.py`: `compute_mt5_performance(bridge, days=90)`, plus the ported
  `_apply_fee`/`_platform_fee_rate` module-private helpers (verbatim, only used here).
- `core_mt5_import.py`: `import_mt5_history(bridge, days=90)` -- calls
  `core_fees_sizing.pnl(...)` (pack 1) instead of `self.pnl(...)`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create the three files, porting each function 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created three files, all well under the 800-line ceiling: `core_total_deposits.py` (50 lines),
`core_mt5_performance.py` (178 lines, including the ported `_apply_fee`/`_platform_fee_rate`
helpers), `core_mt5_import.py` (107 lines, calling pack 1's `core_fees_sizing.pnl()` instead of
`self.pnl()`). All three 1:1 ports, no logic changes, `bridge` taken as an explicit parameter.
Added `tests/core/test_mt5_history_surface.py` (11 tests, 010's exact assertions re-pointed at
the new modules, passing a plain `_FakeBridge` directly instead of setting `self._bridge` on a
`SimulationEngine.__new__()` instance). Full `tests/core/` suite: 244/244 green (233 from packs
1-7 + 11 from this pack). Repo-wide: 575/577 green -- same 2 pre-existing `pytest-asyncio`-
missing failures from earlier packs, unrelated. `engine.py` untouched -- new modules not yet
wired back in.
