# Backend Foundation — gd_copy_signal migration — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date
under Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).
Keep it honest.

_Last updated: 2026-07-19 — 010, 020, 030, 040 done. 050 blocked pending demo credentials AND
a new decision (see Blockers)._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Phase 1 (gd_copy_signal foundation): core extraction done, integration wiring not yet decided
- **Gates:** real-money tasks signed off by the user? n/a yet (050 not started) · tests-first honoured? yes (010, 020, 030, 040 all confirmed red/failing for the right reason before implementing)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [data-access-foundation](010-data-access-foundation.md) | done | agent, 2026-07-19 | `DbAdapter`/`SqliteAdapter`/`connection.py` — 11 tests (10 + 1 regression test added during 030), all green. Confirmed red first (`ModuleNotFoundError`) before implementing. |
| 020 | [characterize-gd-copy-current-behavior](020-characterize-gd-copy-current-behavior.md) | done | agent, 2026-07-19 | 59 tests (38 database + 21 engine) at the time, all green against current code. **Scope note:** engine.py's async orchestration loops are far more externally coupled than expected — left uncovered by agreement with Simon (extract by inspection, cover properly via 050's real run). |
| 030 | [migrate-gd-copy-repo-layer](030-migrate-gd-copy-repo-layer.md) | done | agent, 2026-07-19 | `gd_copy_signal_repo.py` built on the 010 adapter; `close_signal`/`book_partial_close` now atomic. **Found and fixed a real bug**: `create_signal`'s `INSERT OR IGNORE` leaked the previous insert's `lastrowid` on a no-op, caught by 020's suite re-run against the new backend. `database.py` untouched, still in place. |
| 040 | [extract-gd-copy-service-layer](040-extract-gd-copy-service-layer.md) | done | agent, 2026-07-19 | `engine.py` split into `gd_copy_signal_service.py` + 3 mixin files (`_manage`, `_correlate`, `_live_execute`), all well under 800 LOC. 116 tests, all green. **Scope correction:** did NOT delete `engine.py`/`database.py` — 7 files elsewhere (`ui/app.py`, `ui/pages/gd_copy_panel.py`, `ui/pages/remote_node.py`, `core/app_lifecycle.py`, `sync/server.py`, `gd_copy_signal/ml_engine.py`, `telegram_research.py`) still import the old modules; deleting now would break the app. New modules exist in parallel, untested against the real app until wired in. |
| 050 | [demo-account-validation](050-demo-account-validation.md) | blocked | — | Depends on 040 (done). **Sign-off + demo MT5 credentials required.** Also now depends on deciding whether to wire the new service/repo into those 7 call sites first (a "task 045" this pack didn't originally plan for) — see Blockers. |

## Decisions log
- Repo: `forex-refactor2` supersedes `forex-refactor` (source: user, 2026-07-19)
- Data layer: repo/adapter pattern, not a traditional ORM (source: user, 2026-07-19)
- First engine: gd_copy_signal (source: user, 2026-07-19)
- Pack scope: gd_copy_signal only for this pack (source: user, 2026-07-19)
- Sign-off gating: only 050 needs per-task sign-off (source: user, 2026-07-19)

## Blockers / open
- 050 is blocked on Simon supplying demo MT5 credentials/config for `forex-refactor2`.
- **New (2026-07-19):** the new `gd_copy_signal_service.py`/`gd_copy_signal_repo.py` aren't
  wired into the running app yet — 7 files still import the old `engine.py`/`database.py`.
  Need a decision: wire those call sites over now (a new "045" task) before 050's demo
  validation, so 050 actually exercises the code path the live app would use — or run 050
  against the new modules in isolation (e.g. a standalone script importing
  `gd_copy_signal_service` directly) and defer the app-wide wiring to its own later pack.
