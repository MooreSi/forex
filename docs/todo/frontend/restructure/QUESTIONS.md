# Frontend restructure — decisions to confirm

Four choices to settle before phase 2. Each has a **recommendation** — you can say "go with the
recommendations" and only change what you disagree with. Nothing here changes what the app does; it
is all about how far to push the tidying and how much test scaffolding is proportionate.

Answer inline (write `ANSWER:` under each). Answered items stay, annotated — don't delete them.

Phase 1 is not blocked by any of these and can start immediately.

## The decisions (quick list)
1. `app.py` (1,633 lines) — split it, or exempt it like `runtime.py`?
2. `chart.py` (839 lines) — split it, or record it as a deliberate exemption?
3. Do the phase-2 splits need new tests, or is the boot smoke enough?
4. Must phase 1 land in one release, or can it spread across several?

---

## 1. `app.py` is 1,633 lines. Split it, or exempt it?

`app.py` is the app shell: the header ticker, the power and pause dialogs, the Local/Remote mode
toggle, the About/Glossary/Setup content, plus the page wiring that holds it together. A lot of it is
genuinely *composition* — code whose whole job is to arrange other things — and the refactor already
hit this exact wall with `runtime.py`, which stopped at 1,310 lines because full dissolution meant
~90 call sites hand-carrying eight collaborators each. That was recorded as a design consequence,
not a failure.

- **Split the parts that are real components, then stop (Recommended)** — ticker, dialogs, mode
  toggle and the About content move to `components/shell/`; whatever remains is composition and is
  allowed to stay. Probably lands somewhere around 400–600 lines. Honest, and does not invent
  structure to hit a number.
- **Full split to under 800 as a hard target** — keeps the gate uniform with no exemptions, but risks
  manufacturing modules that exist only to move lines out of a file.
- **Leave `app.py` alone entirely** — cheapest, and defensible for a composition root, but the About
  and Glossary content alone is several hundred lines of pure data sitting in the shell file.

ANSWER: PROVISIONAL (2026-08-11, agent under Darren's "complete stage 2" instruction; Darren
confirms) — the recommendation: split the real components (About/Glossary content, dialogs,
ticker where it separates cleanly), let the remaining composition stay. No manufactured modules.
Stage2 phase 1 already moved the About home into `frontend/components/about_home.py`.

## 2. `chart.py` is 839 lines — 39 over the gate. Worth splitting?

It is mostly one large ECharts configuration object. Splitting it would mean separating a config from
the code that consumes it for the sake of 39 lines.

- **Leave it; record a deliberate exemption (Recommended)** — note it in the docs task as "over by
  design, here is why", the same treatment `runtime.py` and `mt5_bridge.py` already get. An exemption
  with a written reason is worth more than a split that fools the gate.
- **Split it** — extract the chart config to its own module. Uniform, cheap, mildly artificial.

ANSWER: PROVISIONAL (2026-08-11, as above) — the recommendation: leave `chart.py`, record it as a
deliberate exemption with its reason (one large ECharts config; splitting config from its one
consumer for 39 lines fools the gate rather than serving it).

## 3. Do the phase-2 splits need new tests?

Splitting a page into a package changes no behaviour: the same functions run in the same order, they
just live in different files. The suite already has `tests/frontend/` proving pages import and the app
boots and serves.

- **Boot smoke + a per-package import test (Recommended)** — proves every new module is reachable and
  the page still renders, without writing behavioural tests for behaviour that isn't new. Keeps the
  coverage ratchet honest since moved code carries its existing tests.
- **Full characterization tests per split page** — pins each page's render output before the move.
  Much more thorough, considerably more work, and for pure file moves it mostly re-proves what the
  import graph already guarantees.
- **Boot smoke only** — cheapest; risks a module that exists but is never imported by anything,
  which is the exact species of dead code the 2026 audit found ~3,000 lines of.

ANSWER: PROVISIONAL (2026-08-11, as above) — the recommendation: boot smoke + a per-package
import/wiring test (`tests/frontend/test_page_packages_are_wired.py` already covers the
NameError-after-split class); no new behavioural tests for moved behaviour.

## 4. Must phase 1 land as one release, or can it spread?

Phase 1 has six tasks. Each is independently green — the contract count just steps down.

- **Spread across releases (Recommended)** — land tasks as they finish. Smaller commits, easier
  reverts, and the money-touching task (1/020) ships alone on its own release after its demo session,
  which is what you want anyway.
- **One release** — the contract goes 59 → 0 in a single version, so the changelog entry is clean.
  But it means a long-lived branch touching every frontend page at once.

ANSWER: PROVISIONAL (2026-08-11, as above) — the recommendation: spread across releases; each task
lands independently green. The money-touching task (phase1/020 trading & risk) ships alone after
Simon's sign-off + demo session — it is NOT part of the stage-2 sweep.

---

## Quick-confirm checklist
- [ ] 1 — how far to split `app.py`?
- [ ] 2 — `chart.py` split, or exempt with a reason?
- [ ] 3 — test depth for phase-2 splits?
- [ ] 4 — phase 1 across releases, or one?
- [ ] Confirmed: task 1/020 (trading & risk) is the only money-touching task, it ships alone, and it
      needs a demo session before it can be called Done.

*Once answered: record each choice in the README's "Decisions locked" table with the date, and
annotate the question above rather than deleting it.*
