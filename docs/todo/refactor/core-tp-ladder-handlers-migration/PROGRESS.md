# Core TP Ladder Handlers Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-run-tp-ladder | done | agent, 2026-07-20 | 11 tests, all green. No `engine.py` bugs found. One test-design correction (early-return-before-SL-trail on full auto-close). |
| 020 | extract-run-tp-ladder | done | agent, 2026-07-20 | Created `core_run_tp_ladder.py` (226 lines). Two self-caught issues fixed before commit: wrong import source for the pct tables, and a real return-gating bug that would have moved SL on an already-closed position when no callback was supplied. 11 new surface tests. 539/539 green in tests/core/. `engine.py` untouched. No real/demo order ever placed/closed/modified. |

## Blockers / open
None. Pack complete. 7 handlers remain in the TP/SL cluster: `_handle_trail_stop`,
`_handle_protected_scale`, `_handle_conservative`, `_handle_scalp_runner`,
`_handle_conservative_trial`, `_handle_no_sl_scale`, and DPM's own handler.
