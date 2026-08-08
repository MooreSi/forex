# Frontend restructure — phase 2: give components a home

**Status:** not started
**Gated on:** phase 1 complete (contract at zero). Rewiring a file and splitting it at the same time doubles the review surface for no benefit — and every page in this phase is also a page in that one.
**Touches money:** no. This phase moves code between files; it does not change a call. Task 020 in phase 1 is the only money-touching task in the pack.

## Goal of this phase

Slim view files that compose, and components that live in `frontend/components/<domain>/`. No file in
`frontend/` above the 800-line gate on an unexplained baseline exemption — the ones that remain over
carry a written reason.

This is the half of the React proposal that was actually about structure. It arrives without a Node
runtime.

## The pattern

`frontend/pages/trading/` already demonstrates it and is the reference for every task here: a slim
`__init__.py` that arranges, and one module per component beside it. Task 010 turns that from an
observed convention into a written one and decides the single open question the pattern leaves —
whether a component belongs in `components/<domain>/` (shared) or beside its page (private).

**Composition, not extraction for its own sake.** A view file's job after this phase is to say *what
appears and in what order*, and nothing else. A module that exists only to hold 200 lines that used
to be somewhere else, and is imported once, and has no name a reviewer would recognise, is not a
component — it is the same file with a seam drawn through it.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-component-convention.md](010-component-convention.md) | Write the convention down and prove it on one page | no |
| [020-settings.md](020-settings.md) | `settings.py` 3,112 → a package | no |
| [030-history.md](030-history.md) | `history.py` 1,416 → a package | no |
| [040-app-shell.md](040-app-shell.md) | `app.py` 1,633 → shell components. **Blocked on QUESTIONS.md Q1.** | no |
| [050-remaining-panels.md](050-remaining-panels.md) | `ai_trade_analysis` 1,250 · `test_panel` 1,246 · `breakout_panel` 919 · `chart` 839 · `reversal_panel` 804 | no |
| [060-ratchet-loc.md](060-ratchet-loc.md) | Drive the `loc` baseline down and record the deliberate exemptions | no |

020–050 are independent of each other once 010 lands, and can run in parallel by different agents.
060 runs last.

## Open questions this phase depends on

[QUESTIONS.md](../QUESTIONS.md) Q1 (how far to split `app.py`), Q2 (`chart.py` — split or exempt) and
Q3 (test depth). Q1 blocks task 040 specifically. The others have defaults recorded and can proceed
under them if the owner has not answered by then — say so in PROGRESS.md if you do.

## Exit criteria

- `frontend/components/` populated and the convention documented where the next session will find it.
- Every view file in `frontend/pages/` is a composer, or has a written reason why not.
- `structure_baseline.json` `loc` totals **down**, no file newly added, regenerated only after the
  totals actually fell.
- Every remaining over-800 file has its exemption reason recorded in the phase-3 docs task.
- App boots, serves, and looks pixel-identical. Headless mode still boots.
- `python -m tools.checks all` green, output pasted into the pack's PROGRESS.md.
