# Core TG Signals Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-tg-signals | done | agent, 2026-07-20 | 6 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-tg-signals | done | agent, 2026-07-20 | Created `core_tg_signals.py` (37 lines, 1:1 port; `tg_reader` taken explicitly). 6 new surface tests. 222/222 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete. This closes out the last trivially-safe pure-read cluster in
`core/engine.py` — everything remaining either touches real MT5 order placement (hard
boundary, out of scope) or needs a fresh scoping decision for moderate-complexity read/write
clusters (`import_mt5_history`, `update_signal`, `compute_mt5_performance`,
`get_total_deposits`, the TP/SL strategy handlers, bot commands, IME, background loops).
