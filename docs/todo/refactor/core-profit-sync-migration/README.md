# Core Profit Sync Migration

Extracts `SimulationEngine._sync_profit`, `_schedule_profit_sync`,
`_profit_sweep`, `_close_full_after_tps` (core/engine.py) into a standalone
module. First pack of the background-loops cluster in the "finish everything
off" push, continuing from the just-finished Telegram bot commands cluster.

`_close_full_after_tps` is the shared dependency injected as an optional
callable (`close_full_after_tps`) across nearly every TP/SL strategy handler
pack already extracted (`core_handle_scale_out.py`, `core_run_tp_ladder.py`,
`core_handle_trail_stop.py`, `core_handle_protected_scale.py`,
`core_handle_conservative.py`, `core_handle_scalp_runner.py`,
`core_handle_conservative_trial.py`, `core_handle_no_sl_scale.py`,
`core_dpm_handler.py`, `core_instant_entry.py`, `core_instant_followup.py`)
-- extracting its real implementation here, alongside the three profit-sync
helpers it depends on, completes that whole family.

  - `_sync_profit`: pulls the real MT5 deal history for a closed position and
    reconciles the app's own P&L estimate against it, correcting the
    simulated account balance on first sync if the two diverge (SL slippage,
    swap, commission).
  - `_schedule_profit_sync`: a bounded retry loop (0/10/60/300/1800-second
    delays, up to ~30 minutes) that keeps calling `_sync_profit` until MT5
    actually has the closing deal available.
  - `_profit_sweep`: a periodic catch-all that finds any closed trade still
    missing its MT5 profit figure and syncs it, tolerating per-trade failures.
  - `_close_full_after_tps`: finalizes a trade once all TPs have closed the
    full position -- but first verifies via `bridge.get_positions()` that MT5
    doesn't still hold a residual position (broker lot-step rounding can
    leave a sliver open); if it does, reopens the trade record and attempts
    to close the residual instead of declaring victory prematurely.

`_schedule_profit_sync`'s real delays are mocked via `asyncio.sleep` patching
in every retry-path test, same as the `/restartbridge` port-polling pack.

See `PROGRESS.md` for task status.
