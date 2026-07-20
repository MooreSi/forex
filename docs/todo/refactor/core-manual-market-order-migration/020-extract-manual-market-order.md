# 020 — Extract manual market order

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** places an order via `open_trade` -- identical call shape to the
original; this pack's own tests only ever pass a fake bridge.

## Decision

Extract into `core_manual_market_order.py` as a single plain async function taking `bridge`
explicitly. Reuses `core_fees_sizing.suggest_lot_size` (pack 1), `core_close_trade.
get_trading_balance` (pack 10), `core_open_trade.open_trade` (pack 11).
`background_open_commentary` taken as an optional injected callable, same pattern as pack 13.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_manual_market_order.py`, porting the function 1:1 (drop `self`, take `bridge`
   explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed at any point.

## Notes

Created `forex_trader/core/core_manual_market_order.py` (189 lines) -- 1:1 port, no logic
changes, `bridge` taken explicitly. Reuses packs 1, 10, 11. Added
`tests/core/test_manual_market_order_surface.py` (12 tests, 010's exact assertions re-pointed
at the new function). Full `tests/core/` suite: 446/446 green (434 from packs 1-13 + 12 from
this pack). Repo-wide: 777/779 green -- same 2 pre-existing `pytest-asyncio`-missing failures
from earlier packs, unrelated. `engine.py` untouched -- new function not yet wired back in.

No real or demo MT5 order was placed at any point in this pack -- every `bridge.place_order`
call across both suites went to a plain in-memory fake, call logs asserted directly. This
leaves `update_signal` as the last deferred piece of the trade-management cluster.
