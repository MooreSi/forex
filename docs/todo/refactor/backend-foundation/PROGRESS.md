# Backend Foundation — gd_copy_signal migration — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date
under Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).
Keep it honest.

_Last updated: 2026-07-19 — ALL of 010-050 done. Phase 1 (backend-foundation) complete._

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
1. Wire `gd_copy_signal_service.py`/`gd_copy_signal_repo.py` into the 7 external call sites
   (`ui/app.py`, `ui/pages/gd_copy_panel.py`, `ui/pages/remote_node.py`, `core/app_lifecycle.py`,
   `sync/server.py`, `gd_copy_signal/ml_engine.py`, `telegram_research.py`) and retire the old
   `engine.py`/`database.py` — this is what makes the refactor actually load-bearing rather than
   parallel/unused code.
2. If further MT5-connected validation is needed for a future engine, the isolated
   "MetaTrader 5 DemoValidation" terminal install (~1.4GB, left in place, not deleted) can be
   reused rather than copied again.
