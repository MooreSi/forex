# Core Trail Stop Handler Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-handle-trail-stop | done | agent, 2026-07-20 | 7 tests, all green. No `engine.py` bugs found. One test-design fix: the TP-marker de-dup relies on pack 5's 2.5s TTL cache, needed to force expiry to test it correctly. |
| 020 | extract-handle-trail-stop | done | agent, 2026-07-20 | Created `core_handle_trail_stop.py` (156 lines, 1:1 port). 7 new surface tests. 553/553 green in tests/core/. `engine.py` untouched. No real/demo order ever placed/closed/modified. |

## Blockers / open
None. Pack complete. 5 handlers remain in the TP/SL cluster.
