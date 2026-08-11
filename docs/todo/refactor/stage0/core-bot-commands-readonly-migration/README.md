# Core Bot Commands (Read-only/Toggle) Migration

Extracts the read-only/reporting and simple-toggle Telegram bot commands
(`_cmd_help`, `_cmd_balance`, `_cmd_daily`, `_cmd_status`, `_cmd_trades`,
`_cmd_pause`, `_cmd_resume`, `_cmd_risk`, `_cmd_strategy`, `_cmd_dpm_on/off`,
`_cmd_ime_on/off`) from `core/engine.py` into a standalone module. First of
three packs covering the Telegram bot commands cluster (26 methods, ~940
lines) -- the trading-action commands (`/close`, `/activate`, `/marketbuy`,
`/marketsell`, `/report`) and the infrastructure/process commands
(`/restartbridge`, `/restartapp`, `/headless`, `/switchlive`, `/switchdemo`)
are separate packs.

`_handle_bot_command` (the command dispatcher/router) is NOT extracted in any
of these three packs -- it's a thin dict-based lookup over all 22 `_cmd_*`
bound methods, most of which live across three different extraction packs.
Wiring it to the extracted functions is a future integration step once the
whole cluster is done; for now it keeps calling `self._cmd_*` in `engine.py`
unmodified, same as every other not-yet-rewired caller throughout this
migration series.

These commands are formatting-heavy (Telegram message text) but otherwise
low-risk: none of them place, close, or modify a live order. Test coverage
focuses on the computed *values* embedded in each response (balances, P&L
signs, win rates, pluralization edge cases) via substring assertions rather
than full exact-string matching, proportionate to how much of each function
is actually branching logic vs. static text.

See `PROGRESS.md` for task status.
