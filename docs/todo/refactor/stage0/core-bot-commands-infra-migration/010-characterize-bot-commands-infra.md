# 010 — Characterize infrastructure bot commands

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none directly (no bridge order calls), but genuinely
sensitive infrastructure: `_cmd_switch_env` repoints the app at a different
SQLite database file and sends real account credentials to the bridge;
`_cmd_restart_app`/`_cmd_headless` spawn a real OS subprocess and can force-exit
the process. Every test mocks these surfaces explicitly -- never exercised for
real.

## Decision

`_start_bridge_process` (called by `_cmd_restart_bridge`) and the
port-listening check are mocked, not extracted here (the former belongs to
the background-loops cluster). `db_module.init`/`config.save_to_yaml`/
`db_module.sync_bridge_credentials_file`/`bridge.send_credentials` are all
mocked for `_cmd_switch_env`. `subprocess.Popen`/`platform_utils.
open_restart_log`/`platform_utils.delayed_relaunch_cmd` are mocked for
`_cmd_restart_app`; the scheduled `_delayed_app_shutdown` task is left to
fire-and-forget naturally (same convention as every `asyncio.create_task`
Telegram-alert call throughout this migration series) -- `asyncio.run()`'s
fast completion means its internal `asyncio.sleep(5)` never gets a chance to
run before the loop closes, so it never reaches the `os._exit(0)` line.

## Tests first (TDD)

- `tests/core/test_bot_commands_infra_characterization.py`:
  - `_cmd_restart_bridge`:
    - `_start_bridge_process` returns `False` -> immediate failure message,
      no port polling.
    - Port never binds within the poll window -> timeout message.
    - Port bound but MT5 not connected -> "not connected yet" message.
    - Connected, `trade_allowed` already true -> "active" message, no
      `enable_autotrading` call.
    - Connected, not allowed, auto-enable reports `already_enabled` -> same
      "active" message.
    - Connected, not allowed, auto-enable fails -> reports the bridge's error.
  - `_cmd_switch_env` (via `_cmd_switch_live`/`_cmd_switch_demo` and directly):
    - No credentials configured for the target environment -> rejected,
      `db_module.init` never called.
    - Credentials present, bridge reports `connected` -> switches, reports
      the login used, `db_module.init` called with the target env's DB path.
    - Credentials present, bridge reports an error status -> config still
      saved, but the bridge error is surfaced with a `/restartbridge` hint.
    - Switching to `live` uses the `live_*` credential fields, not the demo
      ones.
  - `_cmd_restart_app`:
    - Success path: persists `bot_update_offset` *before* spawning, calls
      `subprocess.Popen`, schedules the delayed shutdown, returns the
      5-second-delay message.
    - `subprocess.Popen` raising -> caught, returns a failure message instead
      of propagating.
  - `_cmd_headless`:
    - No/invalid args -> usage message showing current state, no restart
      triggered.
    - `on` -> flag set, delegates to `_cmd_restart_app`, appends the
      UI-unavailable note.
    - `off` -> flag cleared, delegates to `_cmd_restart_app`, appends the
      UI-restored note.

## What to do

1. Write the test file using a fake bridge and mocked infrastructure
   collaborators, calling each method via
   `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — no order-placing
  surface in this pack at all.
- No test writes to a real database file, sends real credentials anywhere,
  spawns a real subprocess, or force-exits the test process.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

15 tests written in `tests/core/test_bot_commands_infra_characterization.py`,
all green on the first run against unmodified `engine.py`. No `engine.py`
bugs found. `db_module.get_mt5_credentials` is mocked directly (rather than
going through `save_mt5_credentials`' real encrypted storage path) -- the
credential encryption subsystem is out of scope for this pack and adds
nothing to what's being characterized here. Confirmed `_cmd_restart_app`'s
scheduled `_delayed_app_shutdown` task never gets a chance to run its real
`asyncio.sleep(5)` (let alone reach `os._exit(0)`) before `asyncio.run()`
closes the loop -- same trusted fire-and-forget pattern used for every
`asyncio.create_task(telegram_alerts.send_message(...))` call throughout
this migration series, verified safe by the test suite completing normally
with no process exit.
