# Core Bridge Watchdog Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-bridge-watchdog | Done | — | 13 tests |
| 020 | extract-bridge-watchdog | Done | — | `core_bridge_watchdog.py`, 107 lines; 14/14 surface tests pass |

## Blockers / open
None. Pack complete. Same 4 pre-existing, unrelated `test_open_trade_*`
failures observed (see `core-max-tp-hit-migration`'s 020 doc).
