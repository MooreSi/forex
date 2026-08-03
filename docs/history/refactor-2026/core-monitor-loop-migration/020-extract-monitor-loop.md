# 020 — Extract monitor loop's real-logic blocks

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** `reconcile_sl_hit`/`check_profit_close_target` can
close a real MT5 position or record a partial close via the same real
collaborators the original code called -- faked in every test here.

## Decision

Extract into `core_monitor_loop.py` as four functions: `check_sl(trade,
tick)` (pure, ported verbatim), `reconcile_sl_hit(trade, tick, price,
reason, bridge, ctx)` (returns `"deferred"`/`"partial"`/`"closed"`),
`check_profit_close_target(trade, tick, profit_close_usd, bridge, ctx)`
(returns whether it closed), `reclaim_ea_managed_trade(trade, strategy)`
(returns whether the EA stays in charge). `ctx` is a
`core_close_trade.CloseTradeContext`, reused rather than re-derived --
`reconcile_sl_hit`/`check_profit_close_target` call the already-extracted
`core_close_trade.record_close`/`core_partial_close.partial_close_trade`
directly. `reclaim_ea_managed_trade` takes `strategy` explicitly since the
original's alert message uses the loop's own possibly-OOH-overridden
`strategy` variable, not `trade.get("strategy")` directly.

`_monitor_loop` itself -- the strategy-handler if/elif dispatch, the
cycle-counter-gated delegation to `_try_activate_pending_signals`/
`_ime_timeout_watchdog`/`_sync_closed_mt5_positions`/`_profit_sweep`/
`_run_dpm_calibration` (all already extracted), and the adaptive sleep
duration -- is explicitly NOT extracted, matching the "permanent thin
orchestration layer" judgment applied to `_handle_bot_command` and every
other pure-dispatch method throughout this migration series. This closes
out the background-loops cluster.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions -- called directly with a
  real DB-backed trade dict and a `CloseTradeContext` instead of driving
  the whole `_monitor_loop` for one iteration; assertions on each
  function's own return value (`"deferred"`/`"partial"`/`"closed"`,
  `True`/`False`) replace the indirect assertions on which faked
  collaborator got called.

## What to do

1. Confirm 010's suite is green.
2. Create `core_monitor_loop.py`, porting the four pieces.
3. Re-run 010's suite (adapted per the decision above) against the new
   functions.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point --
  every order-placing collaborator is always faked.

## Notes

Created `forex_trader/core/core_monitor_loop.py` (169 lines). 18 tests
written in `tests/core/test_monitor_loop_surface.py` -- same scenarios as
010, restructured to call each function directly and assert its return
value plus DB/collaborator side effects. All 18 pass.

Full `tests/core/` suite: 1165 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1498
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.

**This completes the background-loops cluster** (task #20). Every
background loop in `core/engine.py` has now either had its real-logic
sweep body extracted (`core_max_tp_hit`, `core_gd_copy_research`,
`core_email_scheduler`, `core_bridge_watchdog`, and the four pieces here),
or was judged a permanent thin wrapper not worth extracting standalone
(`_tp_ladder_fast_loop`, `_signal_scanner_loop`, `_signal_bus_prune_loop`,
`_data_retention_loop`, `_bot_command_loop`, and now `_monitor_loop`'s own
dispatch shell). The only remaining piece of the whole `core/engine.py`
migration is `_scan_messages` (~1,138 lines, the Telegram signal-parsing
monolith).
