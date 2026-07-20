# Core Manual Market Order Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-manual-market-order | done | agent, 2026-07-20 | 12 tests, all green. No `engine.py` bugs found. Confirmed `take_profit` never reaches the broker-side order except for `STRATEGY_BE_RUNNER`. |
| 020 | extract-manual-market-order | done | agent, 2026-07-20 | Created `core_manual_market_order.py` (189 lines, 1:1 port). 12 new surface tests. 446/446 green in tests/core/. `engine.py` untouched. No real/demo order ever placed. |

## Blockers / open
None. Pack complete. Only `update_signal` remains from the trade-management cluster —
modifies a live order's SL/TP, deferred since pack 8.
