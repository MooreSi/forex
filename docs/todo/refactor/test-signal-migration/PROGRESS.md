# Test Signal Migration — PROGRESS

_Last updated: 2026-07-20 — pack scaffolded, starting 010._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-test-signal-current-behavior | done | agent, 2026-07-20 | 41 tests, all green. No partial-close mechanism -- the double-counting bug class doesn't apply here. `get_signal_by_id` returns `{}` not `None` on missing -- documented. |
| 020 | migrate-test-signal-repo-layer | not started | — | Depends on 010 (done) — ready to start |
| 030 | extract-test-signal-service-layer | not started | — | Depends on 020 |
| 040 | mt5-connectivity-check | not started | — | Depends on 030 |

## Blockers / open
None.
