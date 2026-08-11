# Core Bot Commands (Infrastructure) Migration

Extracts the infrastructure/process Telegram bot commands (`_cmd_restart_bridge`,
`_cmd_restart_app`, `_cmd_headless`, `_cmd_switch_live`, `_cmd_switch_demo`,
`_cmd_switch_env`) from `core/engine.py` into a standalone module. Third and
final pack covering the Telegram bot commands cluster (26 methods total,
paired with `core-bot-commands-readonly-migration` and
`core-bot-commands-trading-migration`), and the final pack before the
background-loops cluster and the `_scan_messages` monolith.

These commands manage real infrastructure -- restarting the MT5 bridge
process, self-relaunching the app process, switching the active MT5 account
environment (which repoints the whole app at a *different SQLite database
file*) -- but each has genuine branching logic worth characterizing on top of
that infrastructure surface (port-binding polls, AutoTrading state checks,
credential presence checks, bridge-response handling). `_start_bridge_process`
(the actual subprocess/Wine-teardown logic `_cmd_restart_bridge` calls) and
`_is_bot_command_authority`/`_bridge_watchdog_loop`/`_bot_command_loop` are
NOT extracted here -- they belong to the separate background-loops cluster.

Given how safety-sensitive `_cmd_switch_env` is (it calls `db_module.init()`
with a *different* database file path and sends real account credentials to
the bridge), every test mocks `db_module.init`/`config.save_to_yaml`/
`db_module.sync_bridge_credentials_file`/`bridge.send_credentials` explicitly
-- no test ever touches a real file path or a real credential value.
`_cmd_restart_app`'s `subprocess.Popen` call and the module-level
`_delayed_app_shutdown` helper (ported verbatim, since it force-exits the
process via `os._exit(0)` in headless mode -- never allowed to actually run in
a test) are likewise fully mocked.

See `PROGRESS.md` for task status.
