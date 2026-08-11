# 010 — Characterize test_signal's current behavior

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same approach as the other two packs: exhaustive coverage of `database.py`'s money-path
functions, plus `engine.py`'s pure/isolable methods and DB-backed helpers. Async orchestration
(`_run_cycle`, `_velocity_loop`, `_watchdog_loop`, `_outcome_loop`, `_execute_live`,
`_run_batch_analysis`) left uncovered by the same established scope note.

## Tests first (TDD)

- `tests/test_signal/test_database_characterization.py` — config, virtual balance
  (`get_virtual_balance`/`set_virtual_balance`/`log_balance`/`get_max_drawdown`), signal CRUD
  (`insert_signal`, `get_open_signals`, `get_all_signals`, `get_recent_closed_signals`),
  `update_signal_status`, `update_signal_triggered`, `set_signal_sl_moved`,
  `update_conservative_levels`, `expire_old_pending_signals`, analysis log, ML feature store
  (`store_ml_features`/`patch_ml_features`/`get_ml_training_data`/`get_ml_features_for_signal`/
  `get_ml_monitor_data`), `update_live_exec_result`, `update_signal_pnl_from_mt5` (already
  correction-based here, unlike breakout_signal pre-fix — confirm this stays true), stats, perf
  breakdowns, `get_consecutive_losses`, `get_perf_by_regime`.
- `tests/test_signal/test_engine_characterization.py` — `_calc_lot_size`, `_calc_pnl_dollars`,
  `_compute_cost_pts`, `_compute_swing_levels` (module-level pure functions), plus
  `_close_signal`'s balance math run against a real isolated DB.

## What to do

1. Write both files against current, unmodified code; confirm green.
2. Prioritize `_close_signal`'s balance sequence — this is the atomicity gap 020 needs to fix
   (4 separate connections today: read balance, write balance, log entry, update signal row).

## Acceptance

- Suite passes against current code.
- Killer test: full lifecycle (insert -> trigger -> TP1 BE-move -> TP3 close) with a
  hand-calculated expected balance.

## Notes

Confirmed: `update_signal_pnl_from_mt5`'s delta-based correction is genuinely bug-free here
(`test_update_signal_pnl_from_mt5_corrects_balance_by_delta` proves it applies only the
correction, not the full new value). No partial-close mechanism exists in this engine at all —
TP1 only moves SL to break-even, so the double-counting bug class found in breakout_signal
cannot occur here.

41 tests total (32 database + 9 engine), all green against current code. `get_signal_by_id`
returns `{}` for a missing row here (not `None` like the other two engines' equivalents) —
documented in a dedicated test so 020 doesn't accidentally "fix" this into a breaking change.
