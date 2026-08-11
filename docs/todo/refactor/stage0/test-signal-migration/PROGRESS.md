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
1. ~~Wire `test_signal_service.py` + friends into the 8 external call sites~~ — **done
   2026-07-21**. `ui/app.py`, `ui/pages/remote_node.py`, `ui/pages/test_panel.py`,
   `core/app_lifecycle.py`, `breakout_signal/adaptive_params.py`, `sync/server.py` now import
   `test_signal_service`/`test_signal_repo`. `gd_copy_signal_correlate.py`'s and
   `breakout_signal/engine.py`'s listed references turned out to be a stale comment and the old
   (now-deleted) file's own self-reference respectively — nothing to wire there. Old `engine.py`
   had zero remaining callers afterward and was deleted; `database.py` kept as the dual-backend
   characterization contract. **`ml_engine.py` migrated too** (see item 2 — the dual-init this
   item originally deferred is gone). **Found and fixed two real, previously-latent bugs while
   wiring this alongside breakout_signal and gd_copy_signal simultaneously for the first time**:
   `forex_trader/src/db/connection.py` held a single global adapter shared by all three engines
   (each `init_db()` call silently clobbered the previous engine's connection); and
   `SqliteAdapter` had no thread-safety even though the app dispatches DB calls from more than
   one thread (`core.database.to_db_thread`'s worker thread for UI reads, main thread for each
   engine's own async loop) — "SQLite objects created in a thread can only be used in that same
   thread", first surfaced as "no such table: test_config" (wrong-engine's connection) then as
   the threading error once the namespace fix was in. Fixed with per-namespace adapters + an
   RLock in the shared connection layer. Verified via full suite (1624/1624) and a real isolated
   `python run.py` boot with the Bounce panel actually visited and rendering live engine state
   in the browser.
2. ~~`ml_engine.py` for all three engines is still unmigrated~~ — **done 2026-07-21** for all
   three (gd_copy_signal 2026-07-21 earlier same day, breakout_signal and test_signal as part of
   this item). Every engine's `ml_engine.py` now imports its own `<engine>_repo` module
   directly; no engine double-initializes the legacy `database` module anymore.
