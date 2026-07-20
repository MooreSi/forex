# Core Update Signal Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete. Trade-management cluster finished._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-update-signal | done | agent, 2026-07-20 | 14 tests, all green. No `engine.py` bugs found. Confirmed the EA-managed-but-unhealthy double-write path (both `modify_order` AND `ea.update_trade` fire) is intentional, not a bug. |
| 020 | extract-update-signal | done | agent, 2026-07-20 | Created `core_update_signal.py` (172 lines, 1:1 port). 14 new surface tests. 474/474 green in tests/core/. `engine.py` untouched. No real/demo order ever modified. |

## Blockers / open
None. Pack complete — and with it, the entire trade-management cluster (packs 9-15) is done.
Remaining in `core/engine.py`: the 13 TP/SL strategy handlers, DPM's own handler, IME, the
~25 Telegram bot commands, ORB, background sync loops, AI fallback parsing — all untouched,
none yet scoped.
