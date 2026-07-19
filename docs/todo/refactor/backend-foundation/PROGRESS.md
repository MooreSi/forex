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
| 050 | [demo-account-validation](050-demo-account-validation.md) | in progress | agent, 2026-07-19 | Connectivity proven: isolated 2nd MT5 terminal (never touches the live one), logged into the demo account, real candle data pulled. Order round-trip (open+close through the new repo) blocked by the agent's own safety policy on financial trades, even demo — needs Simon to either place one manually or accept connectivity-only as sufficient. |

## Decisions log
- Repo: `forex-refactor2` supersedes `forex-refactor` (source: user, 2026-07-19)
- Data layer: repo/adapter pattern, not a traditional ORM (source: user, 2026-07-19)
- First engine: gd_copy_signal (source: user, 2026-07-19)
- Pack scope: gd_copy_signal only for this pack (source: user, 2026-07-19)
- Sign-off gating: only 050 needs per-task sign-off (source: user, 2026-07-19)

## Blockers / open
- **050 is blocked on Simon supplying demo MT5 credentials/config for `forex-refactor2`.** This
  is the only remaining blocker — see resolution below for the wiring question.
- ~~New (2026-07-19): wire the 7 external call sites over now, or run 050 standalone?~~
  **RESOLVED (2026-07-19):** QUESTIONS.md #7 already answered "UI scope: backend-only for now"
  — rewiring `ui/app.py`/`ui/pages/gd_copy_panel.py` etc. would contradict that. 050 runs
  against the new modules via a standalone script (imports `gd_copy_signal_service` +
  `gd_copy_signal_repo` directly, no app wiring). Rewiring the app's 7 call sites is its own
  future pack, not part of this one.
- **New (2026-07-19): order round-trip needs Simon's action.** The agent's own safety policy
  blocks placing any order (even demo) directly. A second, isolated MT5 terminal is set up and
  logged in (`MetaTrader 5 DemoValidation`, PID 88977) — Simon can place one small trade
  manually there and hand the ticket details back for the agent to record through the new repo,
  or accept the connectivity proof already done as sufficient for this task.
