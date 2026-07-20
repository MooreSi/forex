# Test Signal Migration — PROGRESS

_Last updated: 2026-07-20 — pack scaffolded, starting 010._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-test-signal-current-behavior | done | agent, 2026-07-20 | 41 tests, all green. No partial-close mechanism -- the double-counting bug class doesn't apply here. `get_signal_by_id` returns `{}` not `None` on missing -- documented. |
| 020 | migrate-test-signal-repo-layer | done | agent, 2026-07-20 | `test_signal_repo.py` built; `close_signal_with_balance_update()` consolidates a 4-connection sequence into one transaction (worst atomicity gap of the 3 engines, now fixed). 2 new named functions replacing raw-SQL bypasses. 78 tests, all green. |
| 030 | extract-test-signal-service-layer | not started | — | Depends on 020 (done) — ready to start |
| 040 | mt5-connectivity-check | not started | — | Depends on 030 |

## Blockers / open
None.
