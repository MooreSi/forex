# Frontend restructure — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision). This is how
every agent sees where the work is. Keep it honest: a task reported Done that isn't is the exact
failure mode this repo's rules exist to prevent.

_Last updated: 2026-08-06 — pack scaffolded, no code started. QUESTIONS.md unanswered._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

Task 1/020 is money-touching: **not** `done` on a green suite alone — it needs owner sign-off and a
demo session, both recorded in Notes.

## Overall
- Phase 1 (controller boundary): not started — contract at **59**, target 0
- Phase 2 (view decomposition): not started — 8 frontend files on the LOC baseline
- Phase 3 (docs): not started
- **Gates:** `/safe-change` run on 1/020? no · `python -m tools.checks all` green? not run
- **Demo session** (1/020 only): not done
- **Owner decisions:** QUESTIONS.md — 0 of 4 answered

## The number this pack moves

```
python -m tools.refactor_audit.import_contracts --check
  frontend-reaches-the-backend-through-controllers: 59 violation(s), baselined
```

Update this block each time a phase-1 task lands. It is the pack's single honest progress metric.

| Date | Contract count | After task |
|---|---|---|
| 2026-08-06 | 59 | — (baseline at scaffold time) |

## Tasks

| Phase | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 1 | [010 engine panels](phase1-controller-boundary/010-engine-panels.md) | no | not started | — | ~14 imports; `engines_controller` exists but exposes no start/stop/status |
| 1 | [020 trading & risk](phase1-controller-boundary/020-trading-and-risk.md) | **YES** | not started | — | `/safe-change` first. Ships alone. Characterization tests before anything moves. |
| 1 | [030 ai & analytics](phase1-controller-boundary/030-ai-and-analytics.md) | no | not started | — | ~9 imports across 5 pages |
| 1 | [040 notifications & telegram](phase1-controller-boundary/040-notifications-and-telegram.md) | no | not started | — | needs a new `notifications_controller` |
| 1 | [050 backtest & stragglers](phase1-controller-boundary/050-backtest-and-stragglers.md) | no | not started | — | needs a new `backtest_controller`; sweeps whatever 010–040 left |
| 1 | [060 enforce at zero](phase1-controller-boundary/060-enforce-at-zero.md) | no | not started | — | flip `enforced_at_zero=True`, drop the baseline key |
| 2 | [010 component convention](phase2-view-decomposition/010-component-convention.md) | no | not started | — | gates every other phase-2 task |
| 2 | [020 settings.py](phase2-view-decomposition/020-settings.md) | no | not started | — | 3,112 lines — the big one |
| 2 | [030 history.py](phase2-view-decomposition/030-history.md) | no | not started | — | 1,416 lines |
| 2 | [040 app shell](phase2-view-decomposition/040-app-shell.md) | no | not started | — | 1,633 lines. **Blocked on QUESTIONS.md Q1.** |
| 2 | [050 remaining panels](phase2-view-decomposition/050-remaining-panels.md) | no | not started | — | ai_trade_analysis 1,250 · test_panel 1,246 · breakout 919 · chart 839 · reversal 804 |
| 2 | [060 ratchet LOC](phase2-view-decomposition/060-ratchet-loc.md) | no | not started | — | `--update-baseline`, only when totals went DOWN |
| 3 | [010 conventions + React decision](phase3-docs/010-conventions.md) | no | not started | — | `docs/system/rules/70-file-organisation.md`, `30-architecture.md`, CHANGELOG |

## Decisions log
- React/Next.js/shadcn rewrite rejected; restructure in NiceGUI instead (source: user, 2026-08-06)
- No HTTP API or proxy — one process, so the contract at zero delivers what a proxy would (user, 2026-08-06)
- No `SUMMARY.md`/`REVIEW.md`/`BAR.md` in this pack, with reasons recorded in the README doc index (scaffold, 2026-08-06)

## Verification log

Paste the real `python -m tools.checks all` output (or its tail) each time a task lands. Green output
claimed without the paste is not evidence — see the last paragraph of CLAUDE.md for why that rule
exists here.

- 2026-08-06, scaffold: not run — no code changed yet.

## Blockers / open
- **QUESTIONS.md is unanswered.** Task 2/040 (app shell) is blocked on Q1. Everything in phase 1 can
  proceed regardless.
