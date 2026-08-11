# Core Scan Messages: Parse/Classify Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-parse-classify | Done | — | 19 tests |
| 020 | extract-parse-classify | Done | — | `core_scan_messages_parse_classify.py`, 233 lines; 19/19 surface tests pass |

## Blockers / open
None. Pack complete (sub-pack B of `core-scan-messages-migration`). Same 4
pre-existing, unrelated `test_open_trade_*` failures observed (see
`core-max-tp-hit-migration`'s 020 doc).
