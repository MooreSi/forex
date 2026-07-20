# Test Signal Migration — PROGRESS

_Last updated: 2026-07-20 — ALL of 010-040 done. Pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-test-signal-current-behavior | done | agent, 2026-07-20 | 41 tests, all green. No partial-close mechanism -- the double-counting bug class doesn't apply here. `get_signal_by_id` returns `{}` not `None` on missing -- documented. |
| 020 | migrate-test-signal-repo-layer | done | agent, 2026-07-20 | `test_signal_repo.py` built; `close_signal_with_balance_update()` consolidates a 4-connection sequence into one transaction (worst atomicity gap of the 3 engines, now fixed). 2 new named functions replacing raw-SQL bypasses. 78 tests, all green. |
| 030 | extract-test-signal-service-layer | done | agent, 2026-07-20 | `engine.py` split into 6 files (service.py needed a second-pass split -- 1st cut was 1,041 lines, over budget). 3 real bugs caught before commit: wrong DB import in 2 files, a stale-flag notify bug, and a fire-and-forget vs await concurrency change. Fixed an integration gap with unmigrated ml_engine.py. 83 tests, all green. |
| 040 | mt5-connectivity-check | done | agent, 2026-07-20 | Isolated terminal reused, confirmed connectivity + real H1/M15/H4/M5 candle data. Live terminal untouched. Closed after. |

## Blockers / open
None. Pack complete.

**Carried forward for whichever pack comes next:**
1. Wire `test_signal_service.py` + friends into the 8 external call sites (`ui/app.py`,
   `ui/pages/remote_node.py`, `ui/pages/test_panel.py`, `core/app_lifecycle.py`,
   `breakout_signal/engine.py`, `gd_copy_signal/gd_copy_signal_correlate.py`,
   `gd_copy_signal/engine.py`, `sync/server.py`) and retire the old `engine.py`/`database.py`.
2. `ml_engine.py` for all three engines is still unmigrated (out of scope throughout this
   whole `refactor/` series so far) — every engine's service now double-initializes both the
   new repo and the legacy `database` module so `ml_engine.py` keeps working. A future pack
   could migrate the three `ml_engine.py` files too, removing the need for dual-init.
