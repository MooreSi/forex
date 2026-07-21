# Core Engine Wiring

Phase 2 of the `core/engine.py` migration: wires the 49 already-extracted,
already-characterized `forex_trader/core/core_*.py` modules back into
`SimulationEngine` as the methods' real implementations, retiring the
duplicated inline logic. This is the first phase in the whole
`core/engine.py` effort that actually modifies `engine.py` -- every prior
pack (see `docs/todo/refactor/core-*-migration/`) left it completely
untouched by design, since pure extraction-with-characterization-tests
carries zero behavior-change risk. Wiring does carry that risk: a mistake
here changes what the running app actually does.

## Approach

For each method, the wire-in is: replace the method body with a call into
the corresponding `core_*.py` function, passing `self._bridge` and any
collaborator state (caches, cooldown dicts) that already exists as an
instance attribute. The **existing characterization test for that method
must still pass unmodified** after the wire-in -- since that test drives
the method via `SimulationEngine.__new__(SimulationEngine)` and asserts
on real behavior, an unchanged pass is direct proof the delegation is
behaviorally identical, not just "looks equivalent by inspection." Full
`tests/` suite run after every single wire-in (same "expect only the 4
pre-existing `test_open_trade_*` failures, never a new one" bar as every
extraction pack), plus the standing live-app-untouched check on
`/Users/simon/Documents/FOREX` (this phase happens entirely in
`forex-refactor2`; nothing here touches or is deployed to the live app).

## Risk tiers (wiring order: lowest risk first)

| Tier | What | Real-money surface |
|---|---|---|
| 1 | Pure helpers (no DB, no bridge) | none |
| 2 | Read-only / DB-only background sweeps | none |
| 3 | Process-management / SL-only background sweeps | modifies SL, restarts a process -- no order |
| 4 | Trade strategy handlers (13) | modifies SL/TP, partial-closes |
| 5 | Order-placing / order-closing | places or closes a real MT5 order |

## Tracker

| Module | Original method(s) | Tier | Status |
|---|---|---|---|
| `core_monitor_loop.py` (`check_sl`) | `_check_sl` | 1 | Done |
| `core_max_tp_hit.py` (`_tp_level_from_extreme`) | module-level helper | 1 | Done |
| `core_scan_messages_auto_execute.py` (`price_in_entry_range`) | `_price_in_entry_range` | 1 | Done |
| `core_fees_sizing.py` | `pnl` | 1 | Done |
| `core_max_tp_hit.py` (sweep) | `_max_tp_checker_loop` body (sleep/while shell kept), `_backfill_max_tp_hit_corrected` (fully replaced) | 2 | Done |
| `core_gd_copy_research.py` | `_gd_copy_research_loop` body (sleep/while/try shell kept) | 2 | Done |
| `core_mt5_performance.py` | `compute_mt5_performance` (+ `_platform_fee_rate`/`_apply_fee` re-exported for `ui/pages/history.py`) | 2 | Done |
| `core_total_deposits.py` | `get_total_deposits` | 2 | Done |
| `core_mt5_import.py` | `import_mt5_history` | 2 | Done |
| `core_trade_reporting.py` | `get_open_trades`, `get_all_trades`, `compute_performance` | 2 | Done |
| `core_sim_account.py` | `get_sim_account`, `update_sim_balance`, `reset_simulation` | 2 | Done |
| `core_tp_trigger_tracking.py` | `_get_triggered_tps`, `_last_closed_tp`, `_log_tp_wait_diagnostic`, `_check_tp_hits`, `_get_remaining_lots` (+ `self._tp_cache`/`self._tp_wait_log_ts` merged into one `self._tp_trigger_cache` `TPCache` instance) | 2 | Done |
| `core_tg_signals.py` | `get_tg_signals` | 2 | Done |
| `core_signals.py` | `create_signal`, `get_signals`, `activate_signal`, `cancel_signal` | 2 | Done |
| `core_dpm_bookkeeping.py` | `_load_dpm_calibrated`, `_record_dpm_entry`, `_update_dpm_peak`, `_set_dpm_milestone`, `_finalize_dpm_record` (+ `self._dpm_calibrated`/`self._dpm_cal_loaded_at`/`self._dpm_recorded` merged into one `self._dpm_cache` `DPMCache` instance) | 2 | Done |
| `core_email_scheduler.py` | `_email_scheduler_loop` body (sleep/while/try shell kept; both inner `continue`s removed since the extracted function returns early instead) | 2 | Done |
| `core_bot_commands_readonly.py` (13 fns) | `_cmd_*` (readonly) | 2 | Done |
| `core_bridge_watchdog.py` | `_bridge_watchdog_loop` body (sleep/while shell kept; per-cycle state now threaded through a `state` dict, `sleep_for` returned and slept by the shell) | 3 | Done |
| `core_tp_safety_net.py` | `_tp_safety_net_sweep`/`_tp_safety_net_check_trade`/`_compute_be_cost_pts` (+ unused `_TP_SAFETY_NET_ALERT_COOLDOWN` class constant removed) | 3 | Done |
| `core_bot_commands_infra.py` | `_cmd_restart_bridge`/`_cmd_restart_app`/`_cmd_headless`/`_cmd_switch_live`/`_cmd_switch_demo`/`_cmd_switch_env` (+ module-level `_delayed_app_shutdown` removed, now only in the extracted module) | 3 | Done |
| `core_bot_commands_trading.py` | `_cmd_activate`/`_cmd_report` wired now; `_cmd_close`/`_cmd_market_price_buy`/`_cmd_market_price_sell` deliberately deferred until their Tier-5 collaborators (`close_trade`/`open_manual_market_order`) are themselves wired -- see Notes | 3 | Partial |
| `core_pending_signal_activation.py` | `_try_activate_pending_signals` | 3 | Pending |
| `core_mt5_position_sync.py` | `_sync_closed_mt5_positions` | 3 | Pending |
| `core_untracked_positions.py` | `get_untracked_mt5_positions` | 3 | Done |
| `core_profit_sync.py` | `_sync_profit`/`_schedule_profit_sync`/`_profit_sweep` wired; `_close_full_after_tps` deliberately deferred (bare `CloseTradeContext`, same reason as `_cmd_close`) | 3 | Partial |
| `core_ai_signal_fallback.py` | `_try_ai_signal_fallback`/`_push_ai_recovered_created`/`_apply_sl_adjustment`/`_queue_unrecognised`/`_analyse_unrecognised_message` | 3 | Done |
| `core_instant_entry.py` | `_process_instant_entry` | 3 | Pending |
| `core_instant_followup.py` | `_apply_followup_to_instant_trade`/`_find_and_apply_instant_followup`/`_ime_timeout_watchdog` | 3 | Done |
| `core_signal_resolution.py` | signal resolution helpers | 3 | Pending |
| `core_update_signal.py` | `update_signal` | 3 | Done |
| `core_risk_governor.py` | `is_trading_paused`/`_check_pre_trade_filters`/`_rg_day_start_ts`/`_rg_size_and_check`/`_rg_check_halt`/`_rg_apply_halts_on_close` (+ missing `log.warning` parity fix; unused `_RR_BYPASS_SOURCES`/`_RG_MIN_TP1_RR`/`_RG_MAX_STOP_ATR` class constants removed) | 3 | Done |
| `core_run_tp_ladder.py` | `_tp_ladder_fast_loop` body | 3 | Pending |
| `core_orb_report.py` | `build_orb_report`/`orb_auto_execute` | 3 | Pending |
| `core_dpm_handler.py` | `_handle_dynamic_position_management` | 4 | Pending |
| `core_handle_be_runner.py` | `_handle_be_runner` | 4 | Pending |
| `core_handle_conservative.py` | `_handle_conservative` | 4 | Pending |
| `core_handle_conservative_trial.py` | `_handle_conservative_trial` | 4 | Pending |
| `core_handle_no_sl_scale.py` | `_handle_no_sl_scale` | 4 | Pending |
| `core_handle_orb_fixed.py` | `_handle_orb_fixed` | 4 | Pending |
| `core_handle_protected_scale.py` | `_handle_protected_scale` | 4 | Pending |
| `core_handle_scale_out.py` | `_handle_scale_out` | 4 | Pending |
| `core_handle_scalp_runner.py` | `_handle_scalp_runner` | 4 | Pending |
| `core_handle_trail_stop.py` | `_handle_trail_stop` | 4 | Pending |
| `core_monitor_loop.py` (rest) | `_monitor_loop`'s 3 real blocks | 4 | Pending |
| `core_manual_market_order.py` | `open_manual_market_order` | 5 | Pending |
| `core_open_trade.py` | `open_trade` | 5 | Pending |
| `core_open_trade_from_signal.py` | `open_trade_from_signal` | 5 | Pending |
| `core_close_trade.py` | `close_trade`/`_record_close` | 5 | Pending |
| `core_partial_close.py` | `partial_close_trade` | 5 | Pending |
| `core_scan_messages_edit_reparse.py` | `_scan_messages` edit block | 5 | Pending |
| `core_scan_messages_parse_classify.py` | `_scan_messages` parse block | 5 | Pending |
| `core_scan_messages_staleness_strategy.py` | `_scan_messages` staleness/strategy block | 5 | Pending |
| `core_scan_messages_auto_execute.py` (rest) | `_scan_messages` auto-exec block | 5 | Pending |

See `PROGRESS.md` for the running log as wire-ins land.
