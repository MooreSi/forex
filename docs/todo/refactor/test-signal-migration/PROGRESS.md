# Test Signal Migration — PROGRESS

_Last updated: 2026-07-20 — 010, 020, 030 done. 040 up next._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-test-signal-current-behavior | done | agent, 2026-07-20 | 41 tests, all green. No partial-close mechanism -- the double-counting bug class doesn't apply here. `get_signal_by_id` returns `{}` not `None` on missing -- documented. |
| 020 | migrate-test-signal-repo-layer | done | agent, 2026-07-20 | `test_signal_repo.py` built; `close_signal_with_balance_update()` consolidates a 4-connection sequence into one transaction (worst atomicity gap of the 3 engines, now fixed). 2 new named functions replacing raw-SQL bypasses. 78 tests, all green. |
| 030 | extract-test-signal-service-layer | done | agent, 2026-07-20 | `engine.py` split into 6 files (service.py needed a second-pass split -- 1st cut was 1,041 lines, over budget). 3 real bugs caught before commit: wrong DB import in 2 files, a stale-flag notify bug, and a fire-and-forget vs await concurrency change. Fixed an integration gap with unmigrated ml_engine.py. 83 tests, all green. |
| 040 | mt5-connectivity-check | not started | — | Depends on 030 (done) — ready to start |

## Blockers / open
None.
