# Core No-SL-Scale Handler Migration — PROGRESS

_Last updated: 2026-07-20 — pack complete. Last of the four TP/SL handler packs._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-handle-no-sl-scale | Done | — | 15 tests; recurring TP1 BE-move finding + new stale-current_sl-local quirk |
| 020 | extract-handle-no-sl-scale | Done | — | `core_handle_no_sl_scale.py`, 258 lines; 15/15 surface tests pass |

## Blockers / open
None. Pack complete -- this was the last of the `_handle_scalp_runner`/
`_handle_conservative_trial`/`_handle_no_sl_scale` trio from the standing
"continue with all of them" instruction.
