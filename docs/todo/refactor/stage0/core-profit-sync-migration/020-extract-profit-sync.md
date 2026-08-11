# 020 — Extract profit sync + close-full-after-TPs

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** `bridge.close_position` on a detected residual --
identical call shape to the original; this pack's own tests only ever pass
a fake.

## Decision

Extract into `core_profit_sync.py` as four plain functions: `sync_profit(
trade_id, mt5_ticket, bridge)`, `schedule_profit_sync(trade_id, mt5_ticket,
bridge)`, `profit_sweep(bridge)`, `close_full_after_tps(trade_id, mt5_ticket,
close_price, bridge)` -- taking `bridge` explicitly, no `self`.
`close_full_after_tps` constructs a `CloseTradeContext(bridge)` inline to
call `core_close_trade.record_close` (already extracted).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_profit_sync.py`, porting all four functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_profit_sync.py` (174 lines) with four plain
functions (`sync_profit`, `schedule_profit_sync`, `profit_sweep`,
`close_full_after_tps`), each taking `bridge` explicitly. `schedule_profit_sync`/
`close_full_after_tps` call `sync_profit` as a direct module-level sibling
call. `close_full_after_tps` constructs a `CloseTradeContext(bridge)` inline
to call `core_close_trade.record_close` (already extracted).

010's 13 tests ported verbatim into `tests/core/test_profit_sync_surface.py`
-- import changes only (patching `ps.sync_profit`/`ps.record_close` instead
of `SimulationEngine` methods; `record_close`'s call-args assertion updated
to account for the extracted function's explicit 4th `ctx` parameter, which
the original bound method didn't have), zero assertion changes to the
underlying behavior checks. All 13 pass.

Full `tests/core/` suite: 966 passed. Full repo `tests/` suite: 1297 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- verified via the fake bridge's call log in both
the characterization and surface test files.

This is the first pack of the background-loops cluster and completes the
`close_full_after_tps` dependency injected across nearly every TP/SL
strategy handler pack already extracted -- those packs can now be wired to
this real implementation in a future integration step.
