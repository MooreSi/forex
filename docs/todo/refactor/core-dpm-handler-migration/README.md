# Core DPM Handler Migration

Extracts `SimulationEngine._run_dpm_calibration` and
`SimulationEngine._handle_dynamic_position_management` (core/engine.py) into a
standalone module. This is the first pack of the broader "finish everything off"
push through the remaining `core/engine.py` subsystems (DPM handler, AI signal
fallback, ORB report, IME, background loops, Telegram bot commands, and the
`_scan_messages` monolith), continuing directly from the TP/SL strategy handler
cluster (`core-conservative-handler-migration` through
`core-no-sl-scale-handler-migration`).

`_handle_dynamic_position_management` is the adaptive DPM tick handler -- all
parameters (trail distance, BE trigger, TP1 close %) come from
`dpm_engine.compute_adaptive_params` (ATR/ADX/session/momentum/structural swing
levels), already a separate, stable, pure module -- untouched by this pack and
treated as an external collaborator (faked in tests), same as `bridge`.

  1. If TP1 cleared: partial close (momentum-scaled %) -> SL to entry.
  2. Else if unrealised P&L >= adaptive BE trigger: SL to entry.
  3. If SL already at entry: adaptive trailing SL (arithmetic or structural
     swing level, whichever locks in more profit; tightened to 60% of the
     price move if the full trail distance hasn't cleared entry yet).
  4. Mark TP2+ chips for UI (no close -- trailing handles the exit).

`_run_dpm_calibration` is a periodic (2-hour-gated, 20-trade-minimum,
5-new-trades-minimum) sweep that calls `dpm_engine.run_calibration` (also
already extracted/pure, untouched) and persists results to `dpm_calibration` +
`app_config`.

Both reuse `core_dpm_bookkeeping.py`'s `DPMCache`/`load_dpm_calibrated`/
`record_dpm_entry`/`update_dpm_peak`/`set_dpm_milestone` (already extracted),
`core_tp_trigger_tracking.py`'s `TPCache`/`get_triggered_tps`/`get_remaining_lots`,
`core_partial_close.partial_close_trade`, and `core_fees_sizing.pnl`.

See `PROGRESS.md` for task status.
