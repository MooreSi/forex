# Core TP Trigger Tracking Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-tp-trigger-tracking | done | agent, 2026-07-20 | 19 tests, all green. Found and fixed two real issues: a test-design bug (`_check_tp_hits` needs a real `SimulationEngine.__new__()` instance, not a bare stand-in) and a new fixture gotcha — `to_db_thread()` runs on a persistent single-worker `ThreadPoolExecutor` with its own separate thread-local connection cache, needing its own reset helper. No `engine.py` bugs found. |
| 020 | extract-tp-trigger-tracking | done | agent, 2026-07-20 | Created `core_tp_trigger_tracking.py` (139 lines) with a small `TPCache` state carrier for the 3 functions that need cross-call memory or call each other. 19 new surface tests. 200/200 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete — `engine.py` still calls its own original inline logic; wiring the new
module in (or choosing the next `core/engine.py` domain pack) is future work, not yet scoped.
**Flag for future packs**: any pack whose target methods use `db_module.to_db_thread()` needs
the db-worker-thread reset helper documented in 010's Notes, not just the usual
`_reset_thread_local_connection()`.
