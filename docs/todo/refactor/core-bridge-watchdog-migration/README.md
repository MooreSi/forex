# Core Bridge Watchdog Migration

Extracts `SimulationEngine._bridge_watchdog_loop`'s single-cycle health
check (core/engine.py) into a standalone module. Eighth pack of the
background-loops cluster in the "finish everything off" push, continuing
from `core-email-scheduler-migration`.

Unlike every prior sweep-style pack, this loop carries genuine
**cross-iteration state**: `last_restart_at` (monotonic timestamp, for the
180s restart cooldown), `was_connected` (for edge-triggering the
offline/reconnect alerts exactly once per transition, not every tick), and
`consecutive_fails` (must reach `CONSECUTIVE_FAIL_THRESHOLD=2` before a
single failed `/health` call is trusted -- a queued-behind-a-slow-request
false positive on this exact check once triggered a real, disruptive bridge
restart, confirmed live). All three are bundled into one explicit `state`
dict, mutated in place by the extracted function -- same "instance state
taken as an explicit parameter" pattern as `retry_after`/`missing_streak`/
`last_alert` in earlier packs, just three related fields in one dict
instead of one dict each.

The original loop also has **two different post-check sleep durations**,
not one: `CHECK_INTERVAL=60` normally, but `STARTUP_WAIT=20` specifically
right after a just-launched restart (an immediate re-check rather than
waiting a full minute for MT5 to finish logging in). The extracted function
returns this as a float (seconds to sleep next) so `engine.py`'s thin
wrapper can `await asyncio.sleep(await bridge_watchdog_check(...))` and
reproduce the exact original timing -- a fixed-duration wrapper sleep
(the pattern every prior pack used) would silently change this loop's
behavior.

`_start_bridge_process` (still unextracted, belongs to a future
infrastructure pack per `core-bot-commands-infra-migration`'s own
precedent) is taken as an injected async callable, same convention already
established there for the same dependency.

See `PROGRESS.md` for task status.
