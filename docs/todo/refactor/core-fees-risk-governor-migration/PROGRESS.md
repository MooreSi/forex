# Core Fees/Risk Governor Migration — PROGRESS

_Last updated: 2026-07-20 — pack scaffolded, starting 010._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-fees-sizing-risk-governor | done | agent, 2026-07-20 | 51 tests, all green. Found and fixed a real bug in my own test fixtures (thread-local DB connection caching in core/database.py wasn't reset between tests). Confirmed `reset_simulation` already atomic; confirmed `_rg_apply_halts_on_close`'s 2-call gap is real with a forced-failure test. |
| 020 | extract-fees-sizing-risk-governor | not started | — | Depends on 010 (done) — ready to start |

## Blockers / open
None.
