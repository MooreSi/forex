# Core Scan Messages: Staleness + Strategy Resolution Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-staleness-strategy | Done | — | 15 tests |
| 020 | extract-staleness-strategy | Done | — | `core_scan_messages_staleness_strategy.py`, 198 lines; 15/15 surface tests pass |

## Blockers / open
None. Pack complete (sub-pack C of `core-scan-messages-migration`). Same 4
pre-existing, unrelated `test_open_trade_*` failures observed (see
`core-max-tp-hit-migration`'s 020 doc).
