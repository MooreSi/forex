# Frontend restructure

**Spec:** [docs/specs/001-frontend-restructure.md](../../../specs/001-frontend-restructure.md)
**Status:** planning (pre-implementation)
**Domain:** frontend
**Touches money:** YES — one task only: `phase1-controller-boundary/020-trading-and-risk.md`. `/safe-change` governs it; owner sign-off + demo session required before it is Done. Every other task in this pack is money-free.
**Created:** 2026-08-06

## 👋 Picking this up (agents start here)

1. **Read the rules first** — [CLAUDE.md](../../../../CLAUDE.md) and
   [docs/system/rules/10-golden-rules.md](../../../ai/10-golden-rules.md). This app places real orders with
   real money.
2. **Read the plan** — the [anchor spec](../../../specs/001-frontend-restructure.md) for
   Problem / Goal / **What must NOT change**; this hub for the index and decisions;
   [QUESTIONS.md](QUESTIONS.md) for what the owner still has to settle.
3. **Check [PROGRESS.md](PROGRESS.md)** — the shared status log. See what's done / in progress / free.
4. **Claim your task** in PROGRESS.md: set its row to `in progress`, add your name + date under Owner.
5. **Do the work** from the task file — tests first, watch them fail, then implement.
6. **Update PROGRESS.md** as you go — `done` (with commit) or `blocked` (say why).

Gates: `/safe-change` before the trading task · `/split-file` for every phase-2 task ·
`python -m tools.checks all` before every commit.

**This pack changes no behaviour.** If a user could tell the difference, something went wrong.

## What we're building & why

`frontend/` has two structural problems that are the same problem seen from different ends.

**The service boundary is open.** M3 of the 2026 refactor closed the *database* boundary — the
frontend runs no SQL — but not the *service* boundary. The
`frontend-reaches-the-backend-through-controllers` contract has measured the gap since M5: 99 then,
**59 today**. Each is a page that can call a service function on the UI event loop and one more call
site to rewire when a signature moves. This is recorded in
[FINISH_LINE.md](../../../history/refactor-2026/FINISH_LINE.md) as a known correction.

**Components have nowhere to live.** `pages/settings.py` is 3,112 lines, `app.py` 1,633,
`history.py` 1,416 — all baselined past the 800-line gate. `frontend/components/` exists and is
**empty**: created, never used. `pages/trading/` already demonstrates the shape that works — a
package of `_active_trades.py`, `_manual_entry.py`, `_signals_card.py` behind a slim `__init__.py`.
It was never applied elsewhere.

The trigger was a proposal to rewrite the frontend in React/Next.js with shadcn. Rejected on cost:
a Node runtime added to a Windows installer that today bootstraps only Python, a second process to
supervise on the VPS, and 17,842 lines rewritten against an HTTP API that does not exist. But the
two things that proposal was reaching for — **one narrow enforced boundary to the backend** and
**slim views composing domain-scoped components** — are both reachable in NiceGUI and worth doing
regardless. Phase 1 is also precisely the prerequisite a React port would need, so doing it keeps
that option open rather than closing it.

**Why not just leave it.** FINISH_LINE.md M2 recorded "widget-level splits are cosmetic" as the
reason the pages stayed large. That judgement holds for *line-count-driven* splitting and is not
being contradicted here — the justification in this pack is that components need a home, which is
structural. The contract at 59 is the part that is straightforwardly unfinished work.

## What must NOT change

Full list in the [spec](../../../specs/001-frontend-restructure.md#what-must-not-change). The lines
that constrain the tasks here:

- **Order placement, closing, partial closes, sizing.** Rerouting a call site through a controller
  changes which module is imported — never argument order, defaults, return shape or exception type.
  The close path (`close_trade`, `record_close`, `_make_close_trade_ctx`, `partial_close_trade`) is
  frozen: moved verbatim if at all, never reshaped.
- **The four contracts at zero stay at zero**, and the `ui_db` / `sql` gates stay empty. A new
  controller must not become somewhere SQL pools.
- **Every existing test passes unmodified**, except mock-target relocations, each named in its
  commit.
- **Both ratchet baselines may only shrink.** No file may newly enter `structure_baseline.json`.
- **Function-local imports that exist to defer past boot stay function-local** — `app.py:982`,
  `app.py:1127`, `app.py:1246`. Hoisting one is a behaviour change.
- **Headless mode keeps booting**; `no-nicegui-in-the-backend` stays at 2.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live shared status log |
| [QUESTIONS.md](QUESTIONS.md) | Four decisions for the owner, answerable inline |
| [phase1-controller-boundary/](phase1-controller-boundary/README.md) | Drive the contract 59 → 0, then enforce at zero |
| [phase2-view-decomposition/](phase2-view-decomposition/README.md) | Populate `components/<domain>/`, slim the oversized pages |
| [phase3-docs/](phase3-docs/README.md) | Record the conventions and the React decision |

No `SUMMARY.md`: this pack changes nothing a non-technical reader would recognise — the plain-English
digest would say "the app is identical". No `REVIEW.md`: the evidence is the gate output
(`import_contracts --check` = 59) and `wc -l`, both quoted inline and reproducible in one command.
No `BAR.md`: no UI surface is being designed — every screen keeps its current anatomy exactly.

## Roadmap

| Phase | # | Task | Depends on | Money |
|---|---|---|---|---|
| 1 | 010 | [Engine panels → `engines_controller`](phase1-controller-boundary/010-engine-panels.md) | — | no |
| 1 | 020 | [Trading & risk → `trading_controller`](phase1-controller-boundary/020-trading-and-risk.md) | 010 | **YES** |
| 1 | 030 | [AI & analytics → controllers](phase1-controller-boundary/030-ai-and-analytics.md) | — | no |
| 1 | 040 | [Notifications & Telegram → controllers](phase1-controller-boundary/040-notifications-and-telegram.md) | — | no |
| 1 | 050 | [Backtest, config & stragglers](phase1-controller-boundary/050-backtest-and-stragglers.md) | 010–040 | no |
| 1 | 060 | [Flip the contract to zero](phase1-controller-boundary/060-enforce-at-zero.md) | 050 | no |
| 2 | 010 | [Establish the component convention](phase2-view-decomposition/010-component-convention.md) | phase 1 | no |
| 2 | 020 | [Split `settings.py` (3,112)](phase2-view-decomposition/020-settings.md) | 2/010 | no |
| 2 | 030 | [Split `history.py` (1,416)](phase2-view-decomposition/030-history.md) | 2/010 | no |
| 2 | 040 | [Split the app shell `app.py` (1,633)](phase2-view-decomposition/040-app-shell.md) | 2/010 | no |
| 2 | 050 | [Split the remaining oversized panels](phase2-view-decomposition/050-remaining-panels.md) | 2/010 | no |
| 2 | 060 | [Ratchet the LOC baseline down](phase2-view-decomposition/060-ratchet-loc.md) | 2/020–050 | no |
| 3 | 010 | [Document the conventions + the React decision](phase3-docs/010-conventions.md) | phases 1–2 | no |

Phase-1 tasks 010, 030 and 040 are independent and parallelisable. 020 is money-touching and ships
alone. Phase-2 tasks 020–050 are independent of each other once 2/010 lands.

## Decisions locked with the user (2026-08-06)

| Decision | Choice | Source |
|---|---|---|
| React/Next.js/shadcn rewrite | **Rejected.** Node runtime in a Python-only installer + a second VPS process + 17,842 lines against a non-existent API, for benefits (SSR, CDN, code-splitting) that do not apply to a single-user localhost dashboard. | user, 2026-08-06 |
| What to do instead | Close the controller boundary, then decompose views into `components/<domain>/` — the two durable halves of the React proposal, in Python. | user, 2026-08-06 |
| Does this close the React door? | No. Phase 1 is the exact prerequisite a port would need; afterwards it becomes a frontend-only project, decidable later on evidence. | user, 2026-08-06 |
| HTTP API / API proxy | Not built. A proxy bridges two processes; in one process a page calls the controller. The *value* wanted from a proxy — one narrow enforced surface — is delivered by the contract at zero instead. | user, 2026-08-06 |
| Visual redesign | Out of scope entirely. Separate spec if wanted. shadcn is React-only; NiceGUI gives Quasar + Tailwind + `theme.py`. | user, 2026-08-06 |

## Building blocks we reuse (do not rebuild)

| Need | Existing code |
|---|---|
| The component-package pattern to copy | `frontend/pages/trading/` — slim `__init__.py:1-257` composing 10 `_*.py` modules |
| The empty home for components | `frontend/components/__init__.py` — exists, unused |
| A controller that already re-exports service surfaces cleanly | `backend/src/controllers/engines_controller.py:1-30` — and its docstring documents *why* the panels stopped handing it callables |
| The measurement, already wired into the suite | `tools/refactor_audit/import_contracts.py` — `--check` / `--update-baseline`, baseline `import_contracts_baseline.json` |
| The LOC gate and its baseline | `tools/refactor_audit/structure_gates.py`, `structure_baseline.json` |
| The one-command gate | `python -m tools.checks all` |
| Splitting protocol | `/split-file` skill — package dir, import path unchanged |
| Theme hooks, if visual work is ever specced | `frontend/theme.py:1-109` — `THEME_HEAD_CSS`, `get_theme()` |

## Out of scope

- React, Next.js, Node, shadcn — rejected above; revisit only after phase 1, on evidence.
- Any visual or copy change.
- Any behaviour change, new feature, or "while we're here" fix.
- Reshaping the close path (frozen — see CLAUDE.md rule 4).
- Splitting `mt5_bridge.py` (1,335) or any backend file —
  [OPEN_QUESTIONS.md §2](../../../history/refactor-2026/OPEN_QUESTIONS.md), §8.
- Merging the three near-identical engine panels into one parameterised component — real duplication,
  but collapsing it is a behaviour-risk change wearing a restructure's clothes. Noted, not done.
- Building an HTTP API. Only worth it when something outside the process needs one.

## Open questions

Full write-ups with recommendations in [QUESTIONS.md](QUESTIONS.md). Short list:

- **`app.py` (1,633) — split or exempt?** Mostly genuine composition; `runtime.py` set the precedent
  that a curated composition root has a floor. *Default: split ticker/dialogs/mode-toggle into
  `components/shell/`, don't chase the number.*
- **`chart.py` (839) — worth splitting at all?** 39 lines over, largely one ECharts config.
  *Default: leave it, record as a deliberate exemption.*
- **Do phase-2 splits need new tests, or does the boot smoke suffice?** *Default: boot smoke plus a
  per-package import test; no new behavioural tests, because no behaviour is new.*
- **Task ordering vs. release cadence** — can phase 1 ship across several releases, or must it land
  as one? *Default: several; each task is independently green.*
