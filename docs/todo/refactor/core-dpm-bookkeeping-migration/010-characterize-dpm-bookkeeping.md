# 010 — Characterize DPM bookkeeping

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same approach as packs 1-3's 010: characterize against the real `forex_trader.core.database`
module (`db_module`), using a temp file passed to `db_module.init()`.

## Tests first (TDD)

- `tests/core/test_dpm_bookkeeping_characterization.py`:
  - `_load_dpm_calibrated` — empty when `dpm_calibration` has no rows; loads the latest
    `calibrated_at` batch keyed `"{session}_{momentum_bucket}"`; TTL cache means a second call
    within 600s returns the same (stale) dict even if the table changes underneath it; a call
    with `self._dpm_cal_loaded_at` far enough in the past re-queries.
  - `_record_dpm_entry` — first call for a trade_id inserts a row with all snapshot fields;
    second call for the same trade_id is a no-op (dedup via `self._dpm_recorded`, confirmed via
    both the in-memory guard AND the `INSERT OR IGNORE` as a second line of defense).
  - `_update_dpm_peak` — raises the stored `peak_pnl` via `MAX()`; a call with a lower or
    negative P&L doesn't lower it; a call for a trade_id with no existing row is a no-op
    (`UPDATE` with no match).
  - `_set_dpm_milestone` — sets `reached_be`/`reached_tp1`/`reached_tp2` to 1; an invalid
    column name is silently ignored (no exception, no write).
  - `_finalize_dpm_record` — computes `r_multiple` from `final_pnl / initial_risk`; guards
    `initial_risk == 0` to avoid a division error; writes `hold_minutes` from `opened_at`; a
    call for a trade_id with no existing row is a no-op (early return).

## What to do

1. Write the test file against `SimulationEngine`'s real methods. `_load_dpm_calibrated` and
   `_record_dpm_entry` need a minimal engine stand-in exposing `_dpm_calibrated`,
   `_dpm_cal_loaded_at`, `_dpm_recorded` (same `_FakeEngine`-style pattern as earlier packs).
   The other three need no `self`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from packs 1-3.

## Notes

14 tests written in `tests/core/test_dpm_bookkeeping_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed `_load_dpm_calibrated`'s TTL cache
genuinely returns stale data within the 600s window (by design, not a bug) and reloads once
`_dpm_cal_loaded_at` is old enough. Confirmed `_record_dpm_entry`'s dedup guard is the in-memory
set, not the `INSERT OR IGNORE` — a second call with different params is skipped entirely
before ever reaching the DB. Confirmed `_set_dpm_milestone`'s invalid-column guard silently
no-ops (no exception) rather than raising, and `_finalize_dpm_record` guards both zero initial
risk and an unknown trade_id without raising.
