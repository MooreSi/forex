# Backend Foundation — gd_copy_signal migration — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date
under Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).
Keep it honest.

_Last updated: 2026-07-19 — 010 done, 020 starting next._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Phase 1 (gd_copy_signal foundation): in progress
- **Gates:** real-money tasks signed off by the user? n/a yet (050 not started) · tests-first honoured? yes (010 confirmed red before implementing)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [data-access-foundation](010-data-access-foundation.md) | done | agent, 2026-07-19 | `DbAdapter`/`SqliteAdapter`/`connection.py` — 10 tests, all green. Confirmed red first (`ModuleNotFoundError`) before implementing. |
| 020 | [characterize-gd-copy-current-behavior](020-characterize-gd-copy-current-behavior.md) | in progress | agent, 2026-07-19 | No dependencies, can run in parallel with 010 |
| 030 | [migrate-gd-copy-repo-layer](030-migrate-gd-copy-repo-layer.md) | not started | — | Depends on 010 + 020 |
| 040 | [extract-gd-copy-service-layer](040-extract-gd-copy-service-layer.md) | not started | — | Depends on 030 |
| 050 | [demo-account-validation](050-demo-account-validation.md) | not started | — | Depends on 040. **Sign-off + demo MT5 credentials required before implementation.** |

## Decisions log
- Repo: `forex-refactor2` supersedes `forex-refactor` (source: user, 2026-07-19)
- Data layer: repo/adapter pattern, not a traditional ORM (source: user, 2026-07-19)
- First engine: gd_copy_signal (source: user, 2026-07-19)
- Pack scope: gd_copy_signal only for this pack (source: user, 2026-07-19)
- Sign-off gating: only 050 needs per-task sign-off (source: user, 2026-07-19)

## Blockers / open
- 050 is blocked on Simon supplying demo MT5 credentials/config for `forex-refactor2`.
