# 020 — Extract infrastructure bot commands

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none directly; genuinely sensitive infrastructure
(DB file switching, credential sending, subprocess spawning) -- identical
call shape to the original, all mocked in this pack's own tests.

## Decision

Extract into `core_bot_commands_infra.py` as plain functions:
`cmd_restart_bridge(args, bridge, start_bridge_process_fn)`,
`cmd_restart_app(args, bot_offset)`, `cmd_headless(args, restart_app_fn)`,
`cmd_switch_live(args, bridge)`, `cmd_switch_demo(args, bridge)`,
`cmd_switch_env(new_env, bridge)` -- taking `bridge` and the
not-yet-extracted `_start_bridge_process` as an explicit injected callable
(it belongs to a different, not-yet-migrated cluster). `_delayed_app_shutdown`
ported verbatim as a private module-level helper (not imported back from
engine.py).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_bot_commands_infra.py`, porting all six functions plus
   `_delayed_app_shutdown` 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_bot_commands_infra.py` (215 lines) with six
plain functions (`cmd_restart_bridge`, `cmd_restart_app`, `cmd_headless`,
`cmd_switch_live`, `cmd_switch_demo`, `cmd_switch_env`) plus the ported-
verbatim `_delayed_app_shutdown` helper. `cmd_restart_bridge` takes
`start_bridge_process` as an explicit injected async callable (the real
`_start_bridge_process` belongs to the separate, not-yet-migrated
background-loops cluster); `cmd_headless` takes `restart_app` as an
explicit injected async callable so it can delegate without depending on
module-call-order tricks.

010's 15 tests ported verbatim into
`tests/core/test_bot_commands_infra_surface.py`, plus one additional test
(`test_switch_demo_delegates_to_switch_env`) explicitly exercising the
`cmd_switch_demo` wrapper at the surface level -- import changes only
otherwise, zero assertion changes to the ported 15. All 16 pass.

Full `tests/core/` suite: 940 passed. Full repo `tests/` suite: 1271 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No test touched a real file path, sent real
credentials, spawned a real subprocess, or force-exited the test process.

This closes out the Telegram bot commands cluster
(core-bot-commands-readonly-migration + core-bot-commands-trading-migration
+ core-bot-commands-infra-migration). `_handle_bot_command` (the dispatcher)
remains unrewired in `engine.py` -- wiring it to the now fully-extracted 22
`cmd_*` functions across all three modules is a future integration step, out
of scope for the characterize/extract methodology this whole series follows.
