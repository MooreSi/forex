# 020 — Extract MT5 position sync

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none directly -- identical call shape to the
original for its DB-mutating collaborators; this pack's own tests only ever
mock them.

## Decision

Extract into `core_mt5_position_sync.py` as a single plain async function
`sync_closed_mt5_positions(bridge, missing_streak, starting_balance=1000.0)`
-- taking `bridge` and `missing_streak` (the per-trade consecutive-miss
counter dict) explicitly, no `self`. Reuses `core_partial_close.
partial_close_trade`, `core_close_trade.CloseTradeContext`/`record_close`,
`core_profit_sync.sync_profit`/`schedule_profit_sync`,
`core_tp_trigger_tracking.last_closed_tp` (all already extracted).

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_mt5_position_sync.py`, porting the function 1:1.
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_mt5_position_sync.py` (312 lines) as
`sync_closed_mt5_positions(bridge, missing_streak, starting_balance=1000.0)`,
porting the function 1:1. Reuses `core_partial_close.partial_close_trade`,
`core_close_trade.CloseTradeContext`/`record_close`, `core_profit_sync.
sync_profit`/`schedule_profit_sync` (pack 34), and
`core_tp_trigger_tracking.last_closed_tp` (all already extracted).

010's 12 tests ported verbatim into
`tests/core/test_mt5_position_sync_surface.py` -- import changes only
(mocked collaborators patched on the `core_mt5_position_sync` module
instead of `SimulationEngine`), zero assertion changes. All 12 pass,
including both non-obvious findings from 010 (the unreachable-when-no-
open-trades import pass, and the double-`MT5_`-prefixed partial-close
reason string).

Full `tests/core/` suite: 1016 passed. Full repo `tests/` suite: 1347
passed, 2 failed -- the same pre-existing `pytest-asyncio`-missing
failures seen in every prior pack, no new failures.

`engine.py` untouched. This function never places, closes, or modifies a
live MT5 order itself -- verified via the fake bridge's call log across
both test files.
