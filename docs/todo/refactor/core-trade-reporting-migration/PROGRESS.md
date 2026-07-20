# Core Trade Reporting Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-trade-reporting | done | agent, 2026-07-20 | 14 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-trade-reporting | done | agent, 2026-07-20 | Created `core_trade_reporting.py` (172 lines, 1:1 port; `compute_performance` now takes `starting_balance` explicitly). 14 new surface tests. 134/134 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete — `engine.py` still calls its own original inline logic; wiring the new
module in (or choosing the next `core/engine.py` domain pack) is future work, not yet scoped.
`get_untracked_mt5_positions` remains explicitly deferred (bridge-dependent).
