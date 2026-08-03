# Core Bot Commands (Trading Actions) Migration

Extracts the trading-action Telegram bot commands (`_cmd_close`,
`_cmd_activate`, `_cmd_market_price_buy`, `_cmd_market_price_sell`,
`_cmd_report`) from `core/engine.py` into a standalone module. Second of
three packs covering the Telegram bot commands cluster -- the read-only/
toggle commands are `core-bot-commands-readonly-migration`; the
infrastructure/process commands are a third, separate pack.

Unlike the read-only pack, every command here has a real-money or real-I/O
surface, but each one delegates to an already-extracted, already-characterized
function rather than containing new order-placement logic itself:
`_cmd_close` calls `close_trade` (pack 10), `_cmd_activate` calls `open_trade`
(pack 11) after its own signal-validation/entry-zone-gating/lot-sizing logic,
`_cmd_market_price_buy`/`_cmd_market_price_sell` call `open_manual_market_order`
(already extracted) directly, and `_cmd_report` calls `compute_mt5_performance`
(already extracted) plus real email/AI-provider calls. All of these
collaborators are mocked in this pack's tests, the same treatment given to
`open_trade` in the IME packs -- their own real behavior was already
characterized in their own extraction packs.

`_handle_bot_command` (the dispatcher) is still untouched, same as the
read-only pack.

See `PROGRESS.md` for task status.
