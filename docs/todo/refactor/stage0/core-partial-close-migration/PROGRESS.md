# Core Partial Close Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-partial-close | done | agent, 2026-07-20 | 10 tests, all green against unmodified `engine.py`. No bridge involved, no bugs found. |
| 020 | extract-partial-close | done | agent, 2026-07-20 | Created `core_partial_close.py` (78 lines, 1:1 port). 10 new surface tests. 264/264 green in tests/core/. `engine.py` untouched. No real/demo order ever placed. |

## Blockers / open
None. Pack complete. Next up in this cluster: `close_trade`/`_record_close` — calls
`bridge.close_position` directly and is deeply coupled to telegram alerts, `sync.ledger`, DPM
finalization, Risk Governor halt checks, and the circuit breaker. Needs its own dedicated
scoping pass (likely split into sub-pieces) before starting, given the size jump from this pack.
