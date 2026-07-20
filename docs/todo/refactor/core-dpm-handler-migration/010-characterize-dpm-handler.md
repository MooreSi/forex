# 010 — Characterize DPM handler

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs. `dpm_engine.compute_adaptive_params` (ATR/
ADX/session/momentum computation from real candle data) is faked via
`unittest.mock.patch.object` to return a fixed params dict per scenario -- it's an
already-extracted, stable, pure module, out of scope for this pack, same treatment as
`bridge`. `dpm_engine.run_calibration` is faked the same way for the calibration tests.

## Tests first (TDD)

- `tests/core/test_dpm_handler_characterization.py`:
  - `_handle_dynamic_position_management`:
    - TP1 cleared, `tp1_partial_pct > 0`, not yet at BE: partial-closes the momentum-scaled
      %, sets the `reached_tp1` milestone, moves SL to entry (both broker + DB) -- note
      `partial_close_trade`'s own independent TP1 breakeven-move (recurring finding across
      the whole handler-cluster series) has already written the same value to the DB by the
      time this handler's own BE-move runs, so the modify_order call is a redundant-but-
      harmless duplicate.
    - TP1 cleared, `tp1_partial_pct == 0`: no partial close at all, but the handler's own
      SL-to-BE move still runs -- the ONE case in this handler where the SL move isn't
      shadowed by `partial_close_trade`'s side effect, since that function is never called.
    - TP1 cleared, already at BE (trade dict's `sl_moved_to_be` truthy): still partial-closes,
      but the SL-move block is skipped entirely (guarded by `if not sl_at_be`).
    - TP1 cleared, bridge rejects the partial close: the whole function returns immediately --
      no milestone set, no SL move, no further steps. The DPM performance row still gets
      created (via `_record_dpm_entry`, which runs unconditionally near the top of the
      function, before the TP1 branch).
    - TP1 not cleared, unrealised P&L >= the adaptive BE trigger, not yet at BE: SL moves to
      entry, `reached_be` milestone set, returns before the trailing/TP2+ steps.
    - `sl_moved_to_be` DB-read fallback: the passed-in `trade` dict says not-yet-BE, but the
      live DB row already has it set (simulating a caller with a one-cycle-stale dict) --
      the handler re-fetches and correctly treats the trade as already at BE.
    - Trailing (once at BE): plain arithmetic trail update when the price move already clears
      the full trail distance.
    - Trailing: trail distance tightened to 60% of the price move when the full distance
      hasn't cleared entry yet.
    - Trailing: a structural swing level beats the arithmetic trail when it locks in more
      profit -- SL moves to the swing level, not the arithmetic one.
    - Trailing: `should_update` false (computed SL isn't better than current) -> no
      `modify_order` call, no DB write.
    - TP2+ marker: once trailing is locked in, a crossed TP2 (or higher) tier gets a
      `TP{n}_DPM_MARKER` row inserted for the UI -- no partial close.
  - `_run_dpm_calibration`:
    - Called within the 2-hour minimum gap since the last run -> no-op, `dpm_engine.
      run_calibration` never called.
    - Gap satisfied but fewer than 20 total closed DPM trades -> no-op.
    - Gap + 20+ trades satisfied but fewer than 5 new trades since the last recorded count ->
      no-op.
    - All gates satisfied: calls `dpm_engine.run_calibration`, writes one `dpm_calibration` row
      per result, and updates `app_config`'s `dpm_cal_last_run`/`dpm_cal_trade_count`.
    - All gates satisfied but `run_calibration` returns no groups (empty list): no
      `dpm_calibration` rows written, and -- because the `app_config` update happens AFTER the
      empty-results check -- `dpm_cal_last_run`/`dpm_cal_trade_count` are also NOT updated,
      so the next eligible cycle retries immediately rather than waiting out a fresh 2-hour gap.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`) and
   `unittest.mock.patch.object(dpm_engine, "compute_adaptive_params", ...)` /
   `patch.object(dpm_engine, "run_calibration", ...)`, calling
   `SimulationEngine._handle_dynamic_position_management` /
   `SimulationEngine._run_dpm_calibration` via `SimulationEngine.__new__(SimulationEngine)`
   with `_tp_cache = {}`, `_tp_wait_log_ts = {}`, `_dpm_calibrated = {}`,
   `_dpm_cal_loaded_at = 0.0`, `_dpm_recorded = set()`, `_dpm_candles = []`,
   `_dpm_dxy_candles = None`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

16 tests written in `tests/core/test_dpm_handler_characterization.py`, all
green against unmodified `engine.py` on the first run (every scenario was
pre-verified via direct throwaway-script traces before writing final
assertions, given the number of interacting branches). No `engine.py` bugs
found. One recurring finding (6th occurrence across the handler-cluster
series, packs 22-25 plus this one): `partial_close_trade`'s independent
TP1 breakeven-move fires whenever `tp1_partial_pct > 0`, so this handler's
own SL-to-BE move is a redundant-but-harmless duplicate write in that case
-- except when `tp1_partial_pct == 0`, where `partial_close_trade` is never
called at all and the handler's own move is the *only* mechanism, the one
case in this handler where the SL move isn't shadowed.

Also confirmed: `_record_dpm_entry` always runs near the top of the
function (before the TP1 check), so the `dpm_trade_performance` row is
created even on a bridge-rejected TP1 close that returns early with no
milestone set. The `sl_moved_to_be` DB-read fallback (re-fetching when the
passed-in `trade` dict looks stale) works as the inline comment describes.
`_run_dpm_calibration`'s app_config update (`dpm_cal_last_run`/
`dpm_cal_trade_count`) only happens AFTER the empty-results check, so a
calibration run that finds no groups with enough samples does not push out
the next eligible-to-retry time -- confirmed via a dedicated test.
