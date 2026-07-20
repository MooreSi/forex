# Core Monitor Loop Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete. Background-loops cluster (task #20) complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-monitor-loop | Done | — | 18 tests |
| 020 | extract-monitor-loop | Done | — | `core_monitor_loop.py`, 169 lines; 18/18 surface tests pass |

## Blockers / open
None. Pack complete. Same 4 pre-existing, unrelated `test_open_trade_*`
failures observed (see `core-max-tp-hit-migration`'s 020 doc).
