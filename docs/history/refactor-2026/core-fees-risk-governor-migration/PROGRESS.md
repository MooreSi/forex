# Core Fees/Risk Governor Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-fees-sizing-risk-governor | done | agent, 2026-07-20 | 51 tests, all green. Found and fixed a real bug in my own test fixtures (thread-local DB connection caching in core/database.py wasn't reset between tests). Confirmed `reset_simulation` already atomic; confirmed `_rg_apply_halts_on_close`'s 2-call gap is real with a forced-failure test. |
| 020 | extract-fees-sizing-risk-governor | done | agent, 2026-07-20 | Created `core_fees_sizing.py`/`core_sim_account.py`/`core_risk_governor.py` (1:1 ports, all well under 800 lines). Fixed the `_rg_apply_halts_on_close` atomicity gap via one outer `with db_module.db():`, proven with a new forced-failure test. 82/82 green in tests/core/ (51 characterization + 31 new surface tests). `engine.py` untouched — new functions not yet wired back in. |

## Blockers / open
None. Pack complete — `engine.py` still calls its own original inline logic; wiring the new
modules in (or choosing the next `core/engine.py` domain pack) is future work, not yet scoped.
