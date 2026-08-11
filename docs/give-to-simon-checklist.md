# Give-to-Simon readiness checklist

**The gate for handing this app to Simon.** Every line must be green or an
explicitly named deferral that Simon has agreed to. An unchecked box with no
deferral note means NOT ready. Honestly filled — a box ticked that isn't true
is the exact failure this repo's rules exist to prevent.

_Status as of 2026-08-11 (stage-2 sweep). Update in place; this is a keeper
doc, not a work log._

## The gate

- [x] **Usability (stage2 phase 1).** First boot shows the Start Here
  checklist with live status and Fix-this jumps; a Help "?" is on every
  screen; the 10 tabs carry plain-language subtitles; empty states say what
  to do next; About reads as "Set up once / Every day".
  *Caveat: the wording is provisional — Darren reviews
  `docs/questions/006-onboarding-strings.md`.*
- [x] **Migrations (stage2 phase 2).** Schema changes are an ordered,
  numbered registry (`db/migrations.py`) with per-step version stamps;
  legacy DB shapes are fixture-tested to head losslessly; data backfills are
  named and fail loud (`db/backfills.py`); zero `except: pass` in the schema
  path.
- [x] **Test suite trustworthy (stage2 phase 3).** Zero assert-nothing test
  files (gated); broker + runtime carry absolute coverage floors; layout
  hazards gated (packages, ghost testpaths, import-time mutation); fixture
  duplication under a shrinking baseline.
- [ ] **Frontend maintainable (stage2 phase 4).** Target: no pages file over
  800 lines, controller-boundary contract at 0, silent excepts at 0.
  *Open — the boundary stands at 59 baselined; settings.py 3,112 /
  history.py / app.py splits and the hygiene sweep are the remaining stage-2
  work. Not a money risk; a maintainability debt.*
- [x] **Debug mode complete except the seam (stage2 phase 5).** Fakes for
  MT5/Telegram/news/AI/email, all outbound guarded behind `is_debug()`; the
  offline e2e proves signal → open → manage → close on the fakes; the debug
  banner is unmissable.
  *Deferral (Simon): the 3-line `_make_bridge` seam + `run.py` bridge-skip
  that make `FOREX_DEBUG_MODE=1` use the fake bridge in the running app —
  money-touching, needs sign-off + a demo session
  (docs/todo/refactor/infra/local-debug-mode/020).*
- [ ] **Money-path (stage 3 — Simon-gated).** Order-send de-duplication,
  broker↔DB reconciliation, never-record-a-refused-close, protective halts
  on by default. Specced and test-planned in `docs/todo/refactor/stage3/`; ships only
  with Simon's sign-off + demo session. **The app must not be treated as
  handed over until this line is green.**
- [x] **Docs.** HANDOFF.md current (docs/todo/refactor/HANDOFF.md); open decisions
  parked in docs/questions/ (6 items, 0 answered — Simon/Darren triage them
  at handoff); knowledge base updated as work landed.
- [ ] **CHANGELOG updated** for the stage-2 sweep. *Open — phase 7/030.*
- [x] **`python -m tools.checks all` green** at every stage-2 commit (outputs
  in docs/todo/refactor/stage2/PROGRESS.md).
- [ ] **CI green on the branch.** *Open — the workflow exists
  (.github/workflows/checks.yml) but activates on first push; the branch has
  not been pushed (docs/questions/003 — where does the remote live?).*

## How to read this at handoff

Green rows are done and verified. The three open rows are, in order of
weight: the **money-path** (stage 3 — the only one that blocks live use),
the **frontend split** (debt, not danger), and **CHANGELOG/CI** (hygiene).
The demo session that signs off stage 3 is also the natural moment to walk
Simon through Start Here, the debug mode, and the questions queue.
