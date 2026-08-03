# Core Open Trade From Signal Migration (back half) — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-open-trade-from-signal | done | agent, 2026-07-20 | 13 tests, all green. Real race (atomic claim) reproduced deterministically via a patched `db_module.get_circuit_breaker_state` side effect rather than real concurrency. No `engine.py` bugs found. |
| 020 | extract-open-trade-from-signal | done | agent, 2026-07-20 | Created `core_open_trade_from_signal.py` (317 lines, 1:1 port, logging preserved). Reuses packs 11+12. 13 new surface tests. 422/422 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete. This finishes the `open_trade_from_signal` split and the entire
lowest-level trade open/close primitive layer. Remaining trade-management surface:
`open_manual_market_order`, `update_signal` — both still deferred, same risk class (real order
placement/modification).
