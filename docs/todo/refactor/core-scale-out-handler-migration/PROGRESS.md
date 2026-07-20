# Core Scale Out Handler Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-handle-scale-out | done | agent, 2026-07-20 | 8 tests, all green. No `engine.py` bugs found. Found and fixed two of my own test-setup mistakes (needed real `vantage_partial_closes` rows to mark earlier TPs as already-triggered). |
| 020 | extract-handle-scale-out | done | agent, 2026-07-20 | Created `core_handle_scale_out.py` (121 lines, 1:1 port). `close_full_after_tps` taken as an optional injected callable. 9 new surface tests. 501/501 green in tests/core/. `engine.py` untouched. No real/demo order ever placed/closed/modified. |

## Blockers / open
None. Pack complete. `_handle_be_runner` (falls back to Scale Out in ranging markets) can now
reuse this pack's `handle_scale_out` directly. 11 handlers remain in the TP/SL cluster.
