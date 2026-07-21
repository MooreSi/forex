# Backend Foundation — gd_copy_signal migration — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date
under Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).
Keep it honest.

_Last updated: 2026-07-21 — ALL of 010-050 done. Phase 1 (backend-foundation) complete. The
carried-forward wiring item below is now also done -- gd_copy_signal_service.py/
gd_copy_signal_repo.py are load-bearing in the real app, not parallel/unused code anymore._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Phase 1 (gd_copy_signal foundation): DONE. New code (`gd_copy_signal_service.py` +
  `gd_copy_signal_repo.py` + 3 mixins) fully built and tested (120 tests), MT5 connectivity
  proven via an isolated terminal. Not yet wired into the running app (7 external call sites
  still use the old `engine.py`/`database.py`) — that rewiring is separate future work, not
  part of this pack.
- **Gates:** real-money tasks signed off by the user? yes — 050 accepted by Simon as
  connectivity-only, no order round-trip attempted (blocked by agent policy) · tests-first
  honoured? yes (010, 020, 030, 040 all confirmed red/failing for the right reason first)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [data-access-foundation](010-data-access-foundation.md) | done | agent, 2026-07-19 | `DbAdapter`/`SqliteAdapter`/`connection.py` — 11 tests (10 + 1 regression test added during 030), all green. Confirmed red first (`ModuleNotFoundError`) before implementing. |
| 020 | [characterize-gd-copy-current-behavior](020-characterize-gd-copy-current-behavior.md) | done | agent, 2026-07-19 | 59 tests (38 database + 21 engine) at the time, all green against current code. **Scope note:** engine.py's async orchestration loops are far more externally coupled than expected — left uncovered by agreement with Simon (extract by inspection, cover properly via 050's real run). |
| 030 | [migrate-gd-copy-repo-layer](030-migrate-gd-copy-repo-layer.md) | done | agent, 2026-07-19 | `gd_copy_signal_repo.py` built on the 010 adapter; `close_signal`/`book_partial_close` now atomic. **Found and fixed a real bug**: `create_signal`'s `INSERT OR IGNORE` leaked the previous insert's `lastrowid` on a no-op, caught by 020's suite re-run against the new backend. `database.py` untouched, still in place. |
| 040 | [extract-gd-copy-service-layer](040-extract-gd-copy-service-layer.md) | done | agent, 2026-07-19 | `engine.py` split into `gd_copy_signal_service.py` + 3 mixin files (`_manage`, `_correlate`, `_live_execute`), all well under 800 LOC. 116 tests, all green. **Scope correction:** did NOT delete `engine.py`/`database.py` — 7 files elsewhere (`ui/app.py`, `ui/pages/gd_copy_panel.py`, `ui/pages/remote_node.py`, `core/app_lifecycle.py`, `sync/server.py`, `gd_copy_signal/ml_engine.py`, `telegram_research.py`) still import the old modules; deleting now would break the app. New modules exist in parallel, untested against the real app until wired in. |
| 050 | [demo-account-validation](050-demo-account-validation.md) | done | agent, 2026-07-19 | Connectivity proven via an isolated 2nd MT5 terminal (never touched the live one) — logged into the demo account, pulled real candle data. Order round-trip not attempted (blocked by agent policy on financial trades, even demo). **Simon accepted connectivity-only as sufficient.** Isolated terminal closed. |

## Decisions log
- Repo: `forex-refactor2` supersedes `forex-refactor` (source: user, 2026-07-19)
- Data layer: repo/adapter pattern, not a traditional ORM (source: user, 2026-07-19)
- First engine: gd_copy_signal (source: user, 2026-07-19)
- Pack scope: gd_copy_signal only for this pack (source: user, 2026-07-19)
- Sign-off gating: only 050 needs per-task sign-off (source: user, 2026-07-19)

## Blockers / open
None remaining for this pack. All resolved:
- ~~050 blocked on demo MT5 credentials~~ — Simon supplied them 2026-07-19.
- ~~Wire the 7 external call sites now, or run 050 standalone?~~ — resolved standalone;
  QUESTIONS.md #7 already ruled UI rewiring out of scope for this pack.
- ~~Order round-trip needs Simon's action~~ — Simon accepted connectivity-only as sufficient
  2026-07-19 ("happy at this stage it is connecting to mt5"). Isolated terminal closed.

**Carried forward for whichever pack comes next** (not blockers on THIS pack, but real
follow-up work it surfaced):
1. ~~Wire `gd_copy_signal_service.py`/`gd_copy_signal_repo.py` into the 7 external call sites~~
   — **done 2026-07-21**. All 7 (`ui/app.py`, `ui/pages/gd_copy_panel.py`,
   `ui/pages/remote_node.py`, `core/app_lifecycle.py`, `sync/server.py`,
   `gd_copy_signal/ml_engine.py`, `telegram_research.py`) now import
   `gd_copy_signal_service`/`gd_copy_signal_repo` instead of the old `engine`/`database`
   modules. The old `engine.py` (1,295 lines) had zero remaining callers (app or tests) after
   the swap and was deleted outright. `database.py` (752 lines) is kept — the dual-backend
   characterization test (`tests/gd_copy_signal/test_database_characterization.py`) explicitly
   parametrizes over both modules as the equivalence contract, so it's a live reference
   implementation, not dead code. Verified via full suite (1624/1624), a real isolated
   `python run.py` boot, and the GD Copy panel rendering live engine state
   (`Running`, `$1,000.00 Virtual Balance`, `Last cycle: ...`) in the browser with zero
   console errors. `forex_trader/sync/remote_stats_facade.py`'s `_DbFacade`/`_MlFacade`
   classes needed no changes at all — they delegate to whichever module is passed in by
   attribute name, so swapping the underlying module was fully transparent to them.
2. If further MT5-connected validation is needed for a future engine, the isolated
   "MetaTrader 5 DemoValidation" terminal install (~1.4GB, left in place, not deleted) can be
   reused rather than copied again.
3. **Real bug found and fixed 2026-07-21, in this pack's own foundation code**: once
   breakout_signal and test_signal were ALSO wired to run alongside gd_copy_signal in the same
   process (same day, see those packs' own PROGRESS.md), two latent flaws in
   `forex_trader/src/db/connection.py`/`sqlite_adapter.py` surfaced for the first time — neither
   had ever been exercised with more than one engine's repo module live simultaneously before:
   (a) `connection.py`'s `_adapter` was a single bare global, so each engine's `init_db()` call
   silently overwrote the previous engine's connection — only the most-recently-initialized
   engine actually worked, the others got "no such table" errors querying the wrong file; fixed
   with a `namespace` parameter (dict of adapters keyed by engine name, default namespace
   preserves old single-adapter behavior for existing tests). (b) `SqliteAdapter` held one
   persistent `sqlite3.Connection` reused across every call with no thread-safety, but the app
   dispatches DB calls from more than one thread (`core.database.to_db_thread`'s dedicated
   worker thread for most UI reads, direct calls from each engine's own async loop on the main
   thread) — "SQLite objects created in a thread can only be used in that same thread"; fixed
   with `check_same_thread=False` + an `RLock` wrapping every adapter method (RLock, not Lock,
   so `transaction()`'s nested `run()` calls from the same thread don't deadlock). Each
   engine's own `<engine>_repo.py` now wraps `get_db()`/`init_db()` with its own namespace baked
   in, so no other call site (dozens of `get_db().run(...)` etc. per repo file) needed to
   change. `tests/refactor/db/test_adapter.py`/`test_connection.py` still pass unmodified
   (single-threaded, default namespace).
