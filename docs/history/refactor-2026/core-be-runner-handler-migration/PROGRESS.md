# Core BE Runner Handler Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-handle-be-runner | done | agent, 2026-07-20 | 8 tests, all green. No `engine.py` bugs found. |
| 020 | extract-handle-be-runner | done | agent, 2026-07-20 | Created `core_handle_be_runner.py` (97 lines, 1:1 port), reuses pack 17's `handle_scale_out` for the ADX-ranging fallback. 8 new surface tests. 517/517 green in tests/core/. `engine.py` untouched. No real/demo order ever placed/closed/modified. |

## Blockers / open
None. Pack complete. 10 handlers remain in the TP/SL cluster.
