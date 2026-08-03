# Core Close Trade Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-close-trade | done | agent, 2026-07-20 | 18 tests, all green against unmodified `engine.py`. No bugs found. No real/demo order ever placed — fake bridge only, call log asserted directly. |
| 020 | extract-close-trade | done | agent, 2026-07-20 | Created `core_close_trade.py` (368 lines) with `CloseTradeContext` bundling bridge/tp_cache/deferred-subsystem dicts/callbacks. Reuses packs 1 & 4's already-extracted `pnl`/`rg_apply_halts_on_close`/`finalize_dpm_record`. 18 new surface tests. 300/300 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete. Remaining in the trade-management cluster: `open_trade`,
`open_trade_from_signal` (~500 lines, by far the largest single method in `core/engine.py`),
`open_manual_market_order`, and `update_signal` (modifies a live order). All real order
placement/modification — same hard rule applies (no real/demo order ever placed by this work).
