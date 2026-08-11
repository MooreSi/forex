# Core MT5 Deal History Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-mt5-history | done | agent, 2026-07-20 | 11 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-mt5-history | done | agent, 2026-07-20 | Created `core_total_deposits.py`/`core_mt5_performance.py`/`core_mt5_import.py` (50/178/107 lines, all 1:1 ports, `bridge` taken explicitly). 11 new surface tests. 244/244 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete. `update_signal` remains deliberately excluded — it modifies a live MT5
order (`bridge.modify_order`/`ea.update_trade`), so it's deferred to the same risk class as the
13 TP/SL strategy handlers rather than treated as a safe read/backfill. That, plus the
hard-boundary trade-execution methods and the other untouched subsystems (IME, bot commands,
ORB, background loops), is what's left of `core/engine.py`.
