# Backend Foundation — gd_copy_signal migration — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date
under Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).
Keep it honest.

_Last updated: 2026-07-19 — 010, 020, 030 done. 040 up next._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Phase 1 (gd_copy_signal foundation): in progress
- **Gates:** real-money tasks signed off by the user? n/a yet (050 not started) · tests-first honoured? yes (010, 020, and 030 all confirmed red/failing for the right reason before implementing)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [data-access-foundation](010-data-access-foundation.md) | done | agent, 2026-07-19 | `DbAdapter`/`SqliteAdapter`/`connection.py` — 11 tests (10 + 1 regression test added during 030), all green. Confirmed red first (`ModuleNotFoundError`) before implementing. |
| 020 | [characterize-gd-copy-current-behavior](020-characterize-gd-copy-current-behavior.md) | done | agent, 2026-07-19 | 59 tests (38 database + 21 engine) at the time, all green against current code. **Scope note:** engine.py's async orchestration loops are far more externally coupled than expected (live MT5 bridge, `self._main_eng`, `core.database`, a raw cross-engine SQL query) — left uncovered, see task file. Flag to Simon before 040. |
| 030 | [migrate-gd-copy-repo-layer](030-migrate-gd-copy-repo-layer.md) | done | agent, 2026-07-19 | `gd_copy_signal_repo.py` built on the 010 adapter; `close_signal`/`book_partial_close` now atomic. **Found and fixed a real bug**: `create_signal`'s `INSERT OR IGNORE` leaked the previous insert's `lastrowid` on a no-op, caught by 020's suite re-run against the new backend. 020's test file parametrized (fixture-only change) to run unmodified against both backends. 111 tests total, all green. `database.py` untouched, still in place until 040. |
| 040 | [extract-gd-copy-service-layer](040-extract-gd-copy-service-layer.md) | not started | — | Depends on 030 (done) — ready to start, but see 020's scope note first |
| 050 | [demo-account-validation](050-demo-account-validation.md) | not started | — | Depends on 040. **Sign-off + demo MT5 credentials required before implementation.** |

## Decisions log
- Repo: `forex-refactor2` supersedes `forex-refactor` (source: user, 2026-07-19)
- Data layer: repo/adapter pattern, not a traditional ORM (source: user, 2026-07-19)
- First engine: gd_copy_signal (source: user, 2026-07-19)
- Pack scope: gd_copy_signal only for this pack (source: user, 2026-07-19)
- Sign-off gating: only 050 needs per-task sign-off (source: user, 2026-07-19)

## Blockers / open
- 050 is blocked on Simon supplying demo MT5 credentials/config for `forex-refactor2`.
