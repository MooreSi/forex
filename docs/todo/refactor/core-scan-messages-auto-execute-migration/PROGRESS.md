# Core Scan Messages: Auto-Execute Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete. core-scan-messages-migration (all 4 sub-packs) and the entire core/engine.py migration series are now complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-auto-execute | Done | — | 15 tests |
| 020 | extract-auto-execute | Done | — | `core_scan_messages_auto_execute.py`, 327 lines; 15/15 surface tests pass |

## Blockers / open
None. Pack complete (sub-pack D, final piece of `core-scan-messages-migration`
and the entire `core/engine.py` migration series). Same 4 pre-existing,
unrelated `test_open_trade_*` failures observed (see
`core-max-tp-hit-migration`'s 020 doc).
