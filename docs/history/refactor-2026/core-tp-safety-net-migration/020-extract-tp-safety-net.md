# 020 — Extract TP safety net

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order's SL via `bridge.modify_order`
-- identical call shape to the original; this pack's own tests only ever
pass a fake.

## Decision

Extract into `core_tp_safety_net.py` as three plain functions:
`tp_safety_net_sweep(bridge, get_open_trades_fn, last_alert)`,
`tp_safety_net_check_trade(trade, now, bridge, last_alert)`,
`compute_be_cost_pts(trade)` -- taking `bridge` and `last_alert` (the
per-trade cooldown-timestamp dict) explicitly, no `self`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_tp_safety_net.py`, porting all three functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_tp_safety_net.py` (213 lines) with three
functions: `tp_safety_net_sweep(bridge, last_alert)` (async),
`tp_safety_net_check_trade(trade, now, bridge, last_alert)` (async),
`compute_be_cost_pts(trade)` (sync). Reuses `core_trade_reporting.
get_open_trades` (already extracted). `ea_bridge` deferred-import pattern
kept as-is (real, external infrastructure).

010's 15 tests ported verbatim into `tests/core/test_tp_safety_net_surface.py`
-- import changes only, zero assertion changes. All 15 pass.

Full `tests/core/` suite: 1046 passed. Full repo `tests/` suite: 1377
passed, 2 failed -- the same pre-existing `pytest-asyncio`-missing
failures seen in every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- verified via the fake bridge's call log across
both test files.
