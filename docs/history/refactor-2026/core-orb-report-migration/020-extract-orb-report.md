# 020 — Extract ORB report

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** `_orb_auto_execute` creates a pending signal only,
never a live order. Identical call shape to the original; this pack's own
tests only ever pass a fake bridge/DB.

## Decision

Extract into `core_orb_report.py` as four plain functions: `build_orb_report(bridge)`,
`get_orb_target_multiple(bridge)`, `backtest_orb_target_multiple(bridge)`,
`orb_auto_execute(report, bridge, is_active_trader_node)` -- taking `bridge` and
`is_active_trader_node` explicitly, no `self`. `build_orb_report` calls
`get_orb_target_multiple` as a direct module-level sibling call (both live in the
same module). `orb_auto_execute` calls `core_signals.create_signal` (already
extracted). The module-level `_compute_volume_profile` pure helper is ported
verbatim into this module (not imported back from `engine.py`).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_orb_report.py`, porting all four functions plus
   `_compute_volume_profile` 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_orb_report.py` (410 lines) with four plain
functions -- `build_orb_report(bridge)`, `get_orb_target_multiple(bridge)`,
`backtest_orb_target_multiple(bridge)`, `orb_auto_execute(report, bridge,
is_active_trader_node)` -- plus the ported-verbatim `_compute_volume_profile`
pure helper. `build_orb_report` calls `get_orb_target_multiple` as a direct
module-level sibling call. `orb_auto_execute` calls `core_signals.
create_signal` (already extracted). `is_active_trader_node` taken as an
explicit bool, not re-extracted -- belongs to the separate startup/lifecycle
cluster.

010's 16 tests ported verbatim into `tests/core/test_orb_report_surface.py`
-- import changes only (the `datetime` patch target moves to
`core_orb_report.datetime`), zero assertion changes. All 16 pass, including
the traced volume-profile/backtest-median numeric assertions.

Full `tests/core/` suite: 759 passed. Full repo `tests/` suite: 1090 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. This cluster never places, closes, or modifies a
live order -- `orb_auto_execute` only creates a pending, DB-only signal via
`create_signal`.
