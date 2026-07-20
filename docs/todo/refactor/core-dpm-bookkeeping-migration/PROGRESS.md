# Core DPM Bookkeeping Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-dpm-bookkeeping | done | agent, 2026-07-20 | 14 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-dpm-bookkeeping | done | agent, 2026-07-20 | Created `core_dpm_bookkeeping.py` (153 lines) with a small `DPMCache` state carrier for the 2 methods that need cross-call memory; the other 3 are plain functions. 14 new surface tests. 162/162 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete — `engine.py` still calls its own original inline logic; wiring the new
module in (or choosing the next `core/engine.py` domain pack) is future work, not yet scoped.
`_run_dpm_calibration` and `_handle_dynamic_position_management` remain explicitly deferred.
