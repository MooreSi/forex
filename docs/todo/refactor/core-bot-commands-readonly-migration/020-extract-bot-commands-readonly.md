# 020 — Extract read-only/toggle bot commands

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_bot_commands_readonly.py` as plain functions, one per
command, taking `bridge` (and `tg_reader` for `/status`) explicitly, no `self`.
`_handle_bot_command` itself is NOT touched -- it keeps calling `self._cmd_*`
in `engine.py` unmodified until a future integration pass rewires the whole
dispatcher once all three bot-command packs are done.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_bot_commands_readonly.py`, porting all 13 functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_bot_commands_readonly.py` (544 lines) with
13 plain functions (`cmd_help`, `cmd_balance`, `cmd_daily`, `cmd_status`,
`cmd_trades`, `cmd_pause`, `cmd_resume`, `cmd_risk`, `cmd_strategy`,
`cmd_dpm_on/off`, `cmd_ime_on/off`), each taking `bridge` (and `cmd_status`
also `tg_reader`) explicitly. Reuses `core_fees_sizing.pnl`,
`core_sim_account.get_sim_account`, `core_tp_trigger_tracking.last_closed_tp`,
`core_trade_reporting.get_open_trades` (all already extracted).

010's 25 tests ported verbatim into
`tests/core/test_bot_commands_readonly_surface.py` -- import changes only,
zero assertion changes. All 25 pass.

Full `tests/core/` suite: 873 passed. Full repo `tests/` suite: 1204 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. `_handle_bot_command` (the dispatcher) still calls
`self._cmd_*` -- rewiring it to the extracted functions is a future
integration step once all three bot-command packs are done.
