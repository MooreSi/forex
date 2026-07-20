# 020 — Extract trading-action bot commands

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** identical call shape to the original for `close_trade`/
`open_manual_market_order`/`open_trade`; this pack's own tests only ever mock
them.

## Decision

Extract into `core_bot_commands_trading.py` as plain functions:
`cmd_close(args, bridge, starting_balance=1000.0)`,
`cmd_activate(args, bridge, starting_balance=1000.0)`,
`cmd_market_price_buy(args, bridge, starting_balance=1000.0)`,
`cmd_market_price_sell(args, bridge, starting_balance=1000.0)`,
`cmd_report(args, cfg)` -- taking `bridge`/`cfg` explicitly, no `self`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_bot_commands_trading.py`, porting all five functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_bot_commands_trading.py` (242 lines) with
five plain functions (`cmd_close`, `cmd_activate`, `cmd_market_price_buy`,
`cmd_market_price_sell`, `cmd_report`), each taking `bridge` (and `cfg` for
`cmd_report`) explicitly. Reuses `core_close_trade.CloseTradeContext`/
`close_trade`/`get_trading_balance`, `core_fees_sizing.suggest_lot_size`,
`core_manual_market_order.open_manual_market_order`,
`core_mt5_performance.compute_mt5_performance`, `core_open_trade.open_trade`,
`core_risk_governor.price_in_entry_range`, `core_trade_reporting.
get_open_trades` (all already extracted) and `signal_parser.validate_signal`.

010's 18 tests ported verbatim into
`tests/core/test_bot_commands_trading_surface.py` -- import changes only
(mocked collaborators patched on the `core_bot_commands_trading` module
instead of `SimulationEngine`), zero assertion changes. All 18 pass.

Full `tests/core/` suite: 909 passed. Full repo `tests/` suite: 1240 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- `close_trade`/`open_manual_market_order`/
`open_trade` are mocked in every test.
