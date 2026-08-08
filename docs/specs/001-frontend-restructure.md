# SPEC-001 — Frontend restructure: close the service boundary, give components a home

**Status:** Draft
**Owner:** Simon Moore
**Touches money:** yes — the trading-domain rewiring moves call sites that open and close positions. Sign-off + demo session required for that task only.
**Created:** 2026-08-06

---

## Problem

Two things are wrong with `frontend/`, and they are the same thing seen from
different ends.

**The service boundary is open.** M3 of the 2026 refactor closed the
database boundary — the frontend no longer runs SQL — but it did not close
the service boundary. The `frontend-reaches-the-backend-through-controllers`
contract has been measuring the gap since M5: it stood at 99, it stands at
**59** today. Every one of those is a page that can call a service function
directly on the UI event loop, and one more call site to rewire whenever a
service signature moves. `docs/history/refactor-2026/FINISH_LINE.md` records
this as a known correction, not a surprise.

**The views have nowhere to put a component.** `frontend/pages/settings.py`
is 3,112 lines, `app.py` 1,633, `history.py` 1,416 — all baselined past the
800-line gate. `frontend/components/` exists and is **empty**: the directory
was created and never used. Meanwhile `frontend/pages/trading/` shows the
shape that works — a package of `_active_trades.py`, `_manual_entry.py`,
`_signals_card.py` behind a slim `__init__.py`. That pattern was never
applied anywhere else.

The trigger for writing this down was a proposal to rewrite the frontend in
React/Next.js with shadcn. That was rejected on cost: it would add a Node
runtime to a Windows installer that currently bootstraps only Python, put a
second process on the VPS, and mean rewriting 17,842 lines against an HTTP
API that does not exist. But the two things that proposal was actually
reaching for — *one narrow enforced boundary to the backend*, and *slim views
that compose domain-scoped components* — are both achievable in NiceGUI, and
are worth doing on their own merits.

## Goal

After this ships: `frontend/` reaches the backend through `controllers/` and
nothing else, enforced at zero like the other four contracts. Every page is a
slim composer over components that live in `frontend/components/<domain>/`.
No file in `frontend/` sits above the 800-line gate on a baseline exemption.

The app looks and behaves exactly as it does today.

## Non-goals

- **No React, Next.js, Node or shadcn.** Explicitly rejected; see Problem.
  Revisit only if the frontend's growth justifies it, and only once the
  controller boundary is closed — at which point it becomes a frontend-only
  project rather than a full-stack one.
- **No visual redesign.** Not a colour, not a spacing value, not a label.
  Theme work is a separate spec if it is wanted.
- **No behaviour change of any kind.** No new features, no removed features,
  no changed defaults, no "while we're in here" fixes.
- **No reshaping of the close path.** `close_trade`, `record_close`,
  `_make_close_trade_ctx`, `partial_close_trade` are frozen. Call sites may
  be rerouted through a controller; the functions themselves are not touched.
- **No new HTTP API.** Controllers stay in-process Python. An HTTP layer is
  only worth building if something outside the process needs it.
- **Does not split `mt5_bridge.py`** or any backend file — see
  `docs/history/refactor-2026/OPEN_QUESTIONS.md` §2.

## What must NOT change

The most important section, and for this spec it is nearly all of it. This is
a pure restructure: **every observable behaviour stays byte-identical.**

- **Order placement, closing, partial closes and sizing.** The trading-domain
  rewiring changes *which module the frontend imports*, never what that call
  does. Argument order, defaults, return shapes, exception types: identical.
- **The four contracts already enforced at zero** stay at zero:
  `controllers-never-import-repos`, `controllers-never-import-the-database`,
  `services-never-import-controllers`, `frontend-never-imports-the-database`.
- **The `ui_db` and `sql` structure gates** stay empty. A controller
  introduced by this work must not become a place where SQL or DB access
  pools; if a new controller needs data, the owning service exposes a named
  function — the pattern `engines_controller.py` already documents.
- **The coverage ratchet may not fall.** Moving a body between files must
  carry its tests.
- **Every existing test passes unmodified**, with one exception: a
  **mock-target relocation** (`mock.patch("frontend.pages.x.service_fn")` →
  the controller path) is legitimate where a call site moved. Same function,
  same signature, new home. Each one is named in its commit message, per
  `docs/system/rules/40-testing.md`.
- **Both LOC baselines may only shrink.** No file may enter
  `structure_baseline.json` that is not in it today.
- **Headless mode keeps working.** `no-nicegui-in-the-backend` stays at 2 —
  a controller created here must not import NiceGUI.
- **Startup ordering.** Several frontend imports are function-local
  specifically to defer them past app boot (`app.py:982`, `1127`, `1246`).
  Hoisting one to module level is a behaviour change, not a tidy-up.

## Design

Three phases, sequenced. Detail lives in the plan pack at
`docs/todo/frontend/restructure/`.

**Phase 1 — close the service boundary.** Drive
`frontend-reaches-the-backend-through-controllers` from 59 to 0, one domain at
a time, then flip the contract to `enforced_at_zero=True`. Where a controller
does not yet expose what a page needs, add a named function to the controller
that forwards to one service — flat, no logic, per the rule in CLAUDE.md.
Where no controller fits, add one (`notifications_controller`,
`backtest_controller`).

**Phase 2 — give components a home.** Populate `frontend/components/<domain>/`
using `frontend/pages/trading/` as the reference pattern. Each oversized page
becomes a package: a slim `__init__.py` that composes, and one module per
component. Drive the `loc` baseline down as each lands.

**Phase 3 — document the conventions** in `docs/system/rules/`, and record the React
decision so it is not relitigated from scratch in six months.

Layer direction is unchanged throughout: `frontend/` → `controllers/` →
`services/` → `db/`.

## Test plan

Written before the code. The controlling property of a pure restructure is
that behaviour is *pinned first*, then moved.

| Behaviour | Test | Type |
|---|---|---|
| each drained page's calls still reach the same service function with the same args | `test_<page>_wiring.py` | wiring |
| the wiring test can actually detect a wrong target | `test_<page>_wiring_detects_a_wrong_binding` | negative control |
| every new controller function forwards to exactly one service, no logic | `tests/controllers/test_<name>_is_flat.py` | structural |
| the contract reaches zero and stays there | `import_contracts --check` with `enforced_at_zero=True` | structural |
| the flipped contract can still see a violation | `test_frontend_service_contract_detects_a_planted_import` | negative control |
| each split page still imports and renders | `tests/frontend/` boot smoke | wiring |
| no file re-enters the LOC baseline | `structure_gates --check` | structural |
| order-path call sites are byte-identical after rerouting | `test_manual_entry_characterization.py` written against unmodified code **first** | characterization |

Negative controls are not optional here. A restructure's tests are mostly
"this still points at the right thing" assertions, and an assertion that
cannot fail certifies nothing — which is the precise failure this repo's
rules were written after.

## Rollout

- **Not behind a toggle.** There is nothing for a toggle to select: the app
  is identical before and after. The safety mechanism is that every task
  lands independently green.
- **The user sees nothing.** No visual change, no changed labels, no new
  settings. If a user can tell the difference, something went wrong.
- **Reverting** is per-task: each task is one commit against one domain, so
  a bad one reverts without unpicking the others.
- **The money task ships alone**, on its own commit, after a demo session.

## Open questions

1. **`app.py` (1,633) — split or exempt?** It is the app shell: header,
   ticker, power/pause dialogs, the mode toggle. Most of it is genuinely
   composition, and `runtime.py` set the precedent that a curated composition
   root has a floor above 800. *Assumption if unanswered: split the ticker,
   the dialogs and the mode toggle into `components/shell/`, and let whatever
   remains be composition — do not chase the number.*
2. **Does `chart.py` (839) justify a split at all?** It is 39 lines over and
   largely one ECharts config. *Assumption: leave it; note it as a deliberate
   exemption rather than splitting for a line count.*
3. **Do the engine panels (breakout / reversal / test) share enough to be one
   parameterised component?** They look near-identical. *Assumption: do not
   merge them in this spec — that is a behaviour-risk change dressed as a
   restructure. Note the duplication and move on.*

FINISH_LINE.md M2 recorded "widget-level splits are cosmetic" as the reason
frontend pages were left large. That judgement stands for line-count-driven
splitting and is not being contradicted: the justification here is that
components need a home, which is a structural need, not a cosmetic one.

## Verification

Filled in when shipped:

- [ ] full suite green
- [ ] all four gates green
- [ ] `frontend-reaches-the-backend-through-controllers` at 0, `enforced_at_zero=True`
- [ ] no file added to either ratchet baseline; both totals down
- [ ] coverage ratchet not lowered
- [ ] app boots and serves
- [ ] headless mode boots
- [ ] no real or demo order touched by this work or its tests
- [ ] demo session completed for the trading-domain task, signed off by the owner
