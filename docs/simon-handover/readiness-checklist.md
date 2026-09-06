# Give-to-Simon readiness checklist

**The gate for handing this app to Simon.** Every line must be green or an
explicitly named deferral that Simon has agreed to. An unchecked box with no
deferral note means NOT ready. Honestly filled — a box ticked that isn't true
is the exact failure this repo's rules exist to prevent.

_Status as of 2026-08-11 (stage-2 sweep). Update in place; this is a keeper
doc, not a work log._

> **The bar moved, 2026-08-26.** Simon answered Q007 #2 with **B — full
> self-serve**: "handed over" now means he can install, configure and run the
> app alone from the documentation, with nobody else present. That is a higher
> bar than the guided session this list was written against, and it adds a row
> below.
>
> It does **not** waive the Part B demos. The money-path work still has to be
> watched on his demo account before it ships — that is a golden rule, not a
> preference about handover style.

## The gate

- [x] **Usability (stage2 phase 1).** First boot shows the Start Here
  checklist with live status and Fix-this jumps; a Help "?" is on every
  screen; the 10 tabs carry plain-language subtitles; empty states say what
  to do next; About reads as "Set up once / Every day".
  *Caveat: the wording is provisional — Darren reviews
  `docs/todo/refactor/darren-decisions/006-onboarding-strings.md`.*
- [x] **Migrations (stage2 phase 2).** Schema changes are an ordered,
  numbered registry (`backend/migrations/registry.py`) with per-step version stamps;
  legacy DB shapes are fixture-tested to head losslessly; data backfills are
  named and fail loud (`backend/migrations/backfills.py`); zero `except: pass` in the schema
  path.
- [x] **Test suite trustworthy (stage2 phase 3).** Zero assert-nothing test
  files (gated); broker + runtime carry absolute coverage floors; layout
  hazards gated (packages, ghost testpaths, import-time mutation); fixture
  duplication under a shrinking baseline.
- [x] **Frontend maintainable (stage2 phase 4).** Target: no pages file over
  800 lines, controller-boundary contract at 0, silent excepts at 0.
  *Green as of 2026-09-01, measured not remembered. **Re-measured 2026-09-06**
  — still green, but two of the numbers below had drifted; corrected in place.*

  **No file under `frontend/` exceeds 800 lines** — largest is
  `frontend/app/__init__.py` at **789**, then `pages/backtest.py` at 771 and
  `pages/ai_trade_analysis/__init__.py` at 729. *(This row read "largest is
  ai_trade_analysis at 715" until 2026-09-06; that file has grown to 729 and is
  no longer the largest.)* **The ceiling is a hard 800** (`LOC_CEILING` in
  `tools/refactor_audit/structure_gates.py`, and only three files are baselined
  as exempt), so the largest frontend file now has **11 lines of headroom**.
  Worth watching rather than acting on, but the next feature added to
  `frontend/app/__init__.py` is likely to be the one that fails the gate. The
  two pages this row named as
  blocked, `ai_trade_analysis.py` and `test_panel.py`, are packages: both
  bugs ([010](../todo/bugs/010-test-panel-reset-params-nameerror.md),
  [011](../todo/bugs/011-signal-generator-analysis-nameerror.md)) were resolved
  2026-08-27 and the splits followed.

  **The controller-boundary contract is at 1, not the 50 this row recorded**
  (it said 2 until 2026-09-06; one of the two has since gone) — and no frontend
  file imports `backend.src.services` or `backend.src.db` at all. The single
  remaining site is `frontend/app/__init__.py:71` importing `backend.src.app`
  for the engine handle, which is the composition root. Getting to a literal 0
  needs a decision about whether the composition root is a named exception; see
  `docs/todo/refactor/frontend/restructure/PROGRESS.md` task 1/060.

  Silent excepts in the frontend: 0.

  Done since: `settings.py` 3,487 → 11 modules (largest 685), `app.py` 1,746 →
  4, `history.py` 1,592 → 7, plus `chart`, `telegram`, `reversal_panel` and
  `breakout_panel`. On the backend, `ea_bridge.py` 1,947 → 719 across 6
  modules and `core_bot_panel.py` 1,689 → 604 across 6.

  **Two frontend pages remain over 800 and both are blocked on a bug, not on
  effort**: `ai_trade_analysis.py` (1,250) by
  [bugs/011](../todo/bugs/011-signal-generator-analysis-nameerror.md) and
  `test_panel.py` (1,245) by
  [bugs/010](../todo/bugs/010-test-panel-reset-params-nameerror.md). Each page
  carries a latent `NameError` that only fires when a button is clicked; a flat
  module hides it from `test_page_packages_are_wired.py`, a package does not.
  Splitting either one turns a silent dead button into a red gate. **Both fixes
  need Simon's decision — see those two files.**

  The controller-boundary ratchet still stands at 50. Not a money risk; a
  maintainability debt.
- [x] **Debug mode complete except the seam (stage2 phase 5).** Fakes for
  MT5/Telegram/news/AI/email, all outbound guarded behind `is_debug()`; the
  offline e2e proves signal → open → manage → close on the fakes; the debug
  banner is unmissable.
  *Deferral (Simon): the 3-line `_make_bridge` seam + `run.py` bridge-skip
  that make `FOREX_DEBUG_MODE=1` use the fake bridge in the running app —
  money-touching, needs sign-off + a demo session
  (docs/todo/refactor/infra/local-debug-mode/020).*
- [~] **Money-path (stage 3 — Simon-gated).** Order-send de-duplication,
  broker↔DB reconciliation, never-record-a-refused-close, protective halts
  on by default. Ships only with Simon's sign-off + demo session. **The app
  must not be treated as handed over until this line is green.**

  **Demo session held 2026-09-01.** Four of the five are done:
  010 (dedup), 020 (timeout → unknown), 040 (refused close — PASSED live on
  both halves) and 050 (halts — passed after the halt reason was surfaced,
  a gap the demo itself found). Full records in
  [stage3/PROGRESS.md](../todo/refactor/stage3/PROGRESS.md).

  **030 is the one left**, and deliberately: the diff engine and report-only
  pass are in and were seen working on live data during the session, but the
  **repairers are not built**. They would write, and they would write through
  the frozen close path. That is an owner decision, not remaining effort.

  Also still owner-side: the two `enabled` default flips in 050, which are
  ALTER-column defaults and cannot reach an existing install — see
  [011](011-your-halt-settings-do-not-match-what-you-confirmed.md).
  *Ready for him: [session-agenda.md](session-agenda.md) is the sitting;
  the circuit-breaker design review (docs/reviews/2026-08-11) confirms the
  gaps 050 fixes.*
- [ ] **Self-serve documentation (Q007 #2 — the raised bar).** Install,
  configure and first run achievable from the docs alone, by Simon, with no one
  else present: MT5 credentials, Telegram API key, licence activation, and what
  to do when each one fails.

  *Written 2026-08-29:
  [docs/guides/install-from-scratch.md](../guides/install-from-scratch.md)
  covers the install half — Windows and macOS, the three things to have ready
  before starting, and a "when it goes wrong" box on every step drawn from the
  failures the setup script actually branches on. The Start Here checklist and
  Help button cover the in-app half.*

  **Left unticked on purpose.** The bar is "achievable by Simon with no one
  else present", and the only proof of that is Simon doing it on a clean
  machine. Ticking it on the strength of having written it would be marking my
  own homework. Tick it after the first unaided install.
  *Open — this row did not exist until Simon raised the bar on 2026-08-26.*
- [x] **Docs.** HANDOFF.md current (docs/todo/refactor/HANDOFF.md); open decisions
  parked in docs/simon-handover/ (6 items, 0 answered — Simon/Darren triage them
  at handoff); knowledge base updated as work landed.
- [x] **CHANGELOG updated** for the stage-2 sweep ("Unreleased — Road to
  Handoff" section, each claim traceable to a PROGRESS Done row).
- [x] **`python -m tools.checks all` green** at every stage-2 commit (outputs
  in docs/todo/refactor/stage2/PROGRESS.md).
- [x] **CI green on the branch.** First fully green run 2026-08-11 on
  `d2a1661` (run 31506752985, windows-latest): all 8 checks passed after
  the workflow gained its test deps (872e58a) and the review-criticals
  tests went green (d2a1661). Earlier same-day runs failed for known,
  explained reasons (missing pytest; RED-first tests ahead of their fix).

## How to read this at handoff

Green rows are done and verified. The two open rows are, in order of
weight: the **money-path** (stage 3 — the only one that blocks live use)
and the **frontend split** (debt, not danger).
The demo session that signs off stage 3 is also the natural moment to walk
Simon through Start Here, the debug mode, and the questions queue.
