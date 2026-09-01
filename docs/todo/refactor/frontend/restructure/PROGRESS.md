# Frontend restructure — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision). This is how
every agent sees where the work is. Keep it honest: a task reported Done that isn't is the exact
failure mode this repo's rules exist to prevent.

_Last updated: 2026-09-01 — **reconciled against the code.** This pack described a repository
that no longer exists: phase 1 was measured at 59 violations and is at 2, and every phase-2 target
file was split by the `/split-file` queue rather than by these tasks. Statuses below now say what
is true, with the evidence to re-check it. Nothing was marked done on a doc's say-so._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

Task 1/020 is money-touching: **not** `done` on a green suite alone — it needs owner sign-off and a
demo session, both recorded in Notes.

## Overall (2026-09-01)
- Phase 1 (controller boundary): **effectively complete, not formally closed.** The contract is at
  **2**, down from 59. **No frontend file imports `backend.src.services` at all** — verify with
  `grep -rn "backend.src.services" frontend/ --include='*.py' | grep -v __pycache__`, which returns
  nothing. Tasks 020-050 below describe imports that are already gone. Only 1/060 is real work.
- Phase 2 (view decomposition): **goal met by other work.** All nine named files are packages and
  **no file under `frontend/` exceeds 800 lines** (largest: `pages/ai_trade_analysis/__init__.py`
  at 715). The LOC baseline was tightened accordingly on 2026-09-01. Task 060 is done; the rest
  describe splits that have happened.
- Phase 3 (docs): not started. Still real — see below.
- **Gates:** `python -m tools.checks all` green (11/11, 2026-09-01)
- **Demo session** (1/020 only): not needed — see 1/020's row
- **Owner decisions:** QUESTIONS.md — Q1 no longer blocks anything

**Why the drift happened, since this pack exists to prevent exactly that.** The work was real and
it landed; it landed through the `/split-file` queue and the stage-2/stage-3 packs, and nobody came
back to close the rows here. A tracker that overstates what is left is the mirror image of one that
overstates what is done, and it cost a wrong answer to "how much is left?" on 2026-09-01.

## The number this pack moves

```
python -m tools.refactor_audit.import_contracts --check
  frontend-reaches-the-backend-through-controllers: 59 violation(s), baselined
```

Update this block each time a phase-1 task lands. It is the pack's single honest progress metric.

| Date | Contract count | After task |
|---|---|---|
| 2026-08-06 | 59 | — (baseline at scaffold time) |
| 2026-08-11 | 50 | 1/010 engine panels |
| 2026-09-01 | 3 | reconciliation — the intervening drop was not recorded here as it happened |
| 2026-09-01 | 2 | History's fee helpers through the controller (69328df) |

## Tasks

| Phase | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 1 | [010 engine panels](phase1-controller-boundary/010-engine-panels.md) | no | done (2026-08-11) | Claude (for Darren) | engines_controller gains get_engine/engines_running/sub_engines/start_stopped/stop_running; breakout/reversal/test panels + remote_node + app.py rewired (function-local deferrals kept); contract 59→50, baseline tightened; lifecycle + wiring tests with negative controls |
| 1 | [020 trading & risk](phase1-controller-boundary/020-trading-and-risk.md) | **YES** | **obsolete (2026-09-01)** | — | Every import in its Problem table is gone; the pages now go through `trading_controller`, `schedule_controller` and `broker_controller`. No demo needed: nothing here ever moved order-placement code, only who imports it. Verified by the repo-wide grep in Overall. |
| 1 | [030 ai & analytics](phase1-controller-boundary/030-ai-and-analytics.md) | no | **obsolete (2026-09-01)** | — | All nine imports gone. `history.py`'s repo imports — the row this task said to look at hardest — went with the history split; the page now asks `history_controller`. |
| 1 | [040 notifications & telegram](phase1-controller-boundary/040-notifications-and-telegram.md) | no | **obsolete (2026-09-01)** | — | All seven imports gone. A `notifications_controller` exists. |
| 1 | [050 backtest & stragglers](phase1-controller-boundary/050-backtest-and-stragglers.md) | no | **obsolete (2026-09-01)** | — | Gone, including the private `_BROKER_TZ_OFFSET` this task singled out. |
| 1 | [060 enforce at zero](phase1-controller-boundary/060-enforce-at-zero.md) | no | **not started — the only real phase-1 work left** | — | Blocked on a decision, not on effort. The last 2 sites are `frontend/app/__init__.py:70` and `frontend/pages/settings/_email.py:203`, both importing `backend.src.app` for the engine handle and the admin dialog. `frontend/app/__init__.py` is the composition root wiring the app's own startup, which CLAUDE.md already treats as a sanctioned site. Either name that exception in the contract and enforce at zero, or give the two sites a controller. **Decide before flipping** — flipping with an unstated exception is how a gate stops meaning anything. |
| 2 | [010 component convention](phase2-view-decomposition/010-component-convention.md) | no | **superseded (2026-09-01)** | — | It gated the splits, and the splits happened without it. `frontend/components/` exists and is used (`empty_state`, `debug_banner`); the package-with-`_`-prefixed-sections convention is now the de facto one and is written up in `/split-file`. Fold whatever of this is still wanted into 3/010 rather than doing it standalone. |
| 2 | [020 settings.py](phase2-view-decomposition/020-settings.md) | no | **done by other work (2026-09-01)** | `/split-file` queue | `frontend/pages/settings/` is a package of 11 modules, 3,601 lines total, largest `_email.py` at 685. |
| 2 | [030 history.py](phase2-view-decomposition/030-history.md) | no | **done by other work (2026-09-01)** | `/split-file` queue | `frontend/pages/history/` is a package, 1,687 lines total, all modules under the ceiling. |
| 2 | [040 app shell](phase2-view-decomposition/040-app-shell.md) | no | **done by other work (2026-09-01)** | `/split-file` queue | `frontend/app/` is a package, 1,827 lines total, largest `__init__.py` at 673. QUESTIONS.md Q1 no longer blocks it. |
| 2 | [050 remaining panels](phase2-view-decomposition/050-remaining-panels.md) | no | **done by other work (2026-09-01)** | `/split-file` queue | All five are packages. Largest single file left anywhere under `frontend/` is `pages/ai_trade_analysis/__init__.py` at 715. |
| 2 | [060 ratchet LOC](phase2-view-decomposition/060-ratchet-loc.md) | no | **done (2026-09-01)** | Claude | Five loc entries removed, one lowered; the two frontend entries named files that no longer exist, and three cluster files are now under the ceiling entirely. Reasons in `structure_baseline.json` `_tightened["2026-09-01"]`. Found and fixed a defect doing it: `--update-baseline` was deleting `_comment`, `_raised` and `_tightened` on every run. |
| 3 | [010 conventions + React decision](phase3-docs/010-conventions.md) | no | **not started — the only real work left in this pack** | — | Now the whole of it, alongside 1/060. Write the package convention down, close the React question, and update `70-file-organisation.md` (whose split queue still names four files that are already packages) and `30-architecture.md`. |

## Decisions log
- React/Next.js/shadcn rewrite rejected; restructure in NiceGUI instead (source: user, 2026-08-06)
- No HTTP API or proxy — one process, so the contract at zero delivers what a proxy would (user, 2026-08-06)
- No `SUMMARY.md`/`REVIEW.md`/`BAR.md` in this pack, with reasons recorded in the README doc index (scaffold, 2026-08-06)

## Verification log

Paste the real `python -m tools.checks all` output (or its tail) each time a task lands. Green output
claimed without the paste is not evidence — see the last paragraph of CLAUDE.md for why that rule
exists here.

- 2026-08-06, scaffold: not run — no code changed yet.
- 2026-09-01, reconciliation:

```
Running 11 check(s)
  structure gates ok · import contracts ok · runtime facade ok · orphan modules ok
  undefined names ok · unawaited coroutines ok · late binding ok · boot smoke ok
  doc links ok · test suite ok · coverage ratchet ok
All checks passed.
```

## Blockers / open
- ~~**QUESTIONS.md is unanswered.** Task 2/040 (app shell) is blocked on Q1.~~ Moot as of
  2026-09-01: the app shell was split anyway and Q1 blocks nothing.
- **1/060 needs a decision, not effort.** See its row: two `backend.src.app` sites remain, one of
  them the composition root. Name the exception or remove the sites, then enforce at zero.
