# 010 — Establish the component convention

**Status:** not started
**Depends on:** phase 1 complete
**Touches money:** no
**Layer:** frontend
**Leverage:** `frontend/pages/trading/` — the pattern already exists and works; this names it

## Problem

`frontend/components/__init__.py` exists and is **empty**. The directory was created and never used.
Meanwhile `frontend/pages/trading/` is a working component package — `_active_trades.py`,
`_manual_entry.py`, `_signals_card.py`, `_strategy_cards.py` and six more behind a 257-line
`__init__.py` that composes them.

So the codebase holds two contradictory statements about where components go, and neither is written
down. Every other page took the third option and grew to 3,112 lines.

The question the existing pattern does not answer: `trading/`'s modules are `_`-prefixed and private
to that page. `components/` implies something shared. Nothing says which a given component should be,
so without a rule the next person guesses, and the guess will differ from the last one.

## Decision

Write the rule, then prove it by applying it to exactly one page.

Proposed rule, to be confirmed as it is applied:

- **`frontend/pages/<page>/`** — a package per view. `__init__.py` composes and does nothing else;
  `_<component>.py` modules hold components private to that view. This is `trading/`, unchanged.
- **`frontend/components/<domain>/`** — components used by **more than one** view. A component moves
  here on its second caller, not in anticipation of one.
- **`frontend/components/shared/`** — genuinely generic primitives (a stat row, a labelled badge, a
  card shell) with no domain knowledge at all.

The "move on the second caller" rule is the load-bearing part. Speculative sharing is how a component
directory fills with things one page uses via three optional parameters.

Prove it on **`edge_dashboard.py` (195 lines)** — small, not on the LOC baseline, and low-risk. If the
rule cannot be applied cleanly to a 195-line page, it will not survive `settings.py`.

## What must NOT change

- Import paths that anything outside `frontend/pages/` depends on. `/split-file`'s whole premise is a
  package directory that keeps the module's import path — `frontend.pages.edge_dashboard` still
  imports after it becomes a package.
- Rendering. Same widgets, same order, same classes, same text. Pixel-identical.
- `frontend/pages/trading/` — it is the reference, not a target. Leave it alone.
- The `ui.timer()` refresh intervals on any page touched.

## Tests first (TDD)

Test depth here is [QUESTIONS.md](../QUESTIONS.md) Q3; the default is boot smoke plus a per-package
import test, which is what these are.

- `tests/frontend/test_component_packages.py::test_every_component_module_is_imported_by_its_package`
  — structural, and the one that matters. Walks `frontend/pages/*/` and `frontend/components/*/` and
  asserts every `_*.py` module is reachable from its `__init__.py`. This is the guard against the
  failure the 2026 audit found ~3,000 lines of: extracted code nothing calls.
- `tests/frontend/test_component_packages.py::test_the_walker_notices_an_orphan_module`
  — **negative control**. Plant an unimported module in a temp package; assert it is reported.
- `tests/frontend/test_edge_dashboard_renders.py::test_the_page_still_imports_and_builds`
  — wiring, via the existing `tests/frontend/` boot-smoke helpers.

## What to do

1. Write the tests; run them; confirm they fail for the right reason.
2. Write the convention into `docs/system/rules/70-file-organisation.md` — where components go, the
   second-caller rule, and `trading/` named as the worked example. Phase 3 revisits it once four more
   pages have tested it; getting it written now is what makes tasks 020–050 consistent.
3. Convert `edge_dashboard.py` → `frontend/pages/edge_dashboard/` per the rule.
4. If anything in it is genuinely shared, move it to `components/<domain>/` — and if nothing is, say
   so. An honest "no shared components found in the first page" is a real result and keeps
   `components/` empty until something earns a place in it.
5. `python -m tools.checks all`.

## Where

- `docs/system/rules/70-file-organisation.md` — the convention
- `frontend/pages/edge_dashboard.py` → `frontend/pages/edge_dashboard/`
- `frontend/components/` — populated only if the first page genuinely produces something shared

## Acceptance

- The convention is written where the next session will find it without being told it exists.
- `edge_dashboard` is a package; `frontend.pages.edge_dashboard` still imports unchanged.
- The orphan-module test passes **and** is proven able to fail.
- **The killer test:** open the Edge Dashboard before and after — identical, down to spacing and
  refresh cadence.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- This task gates 020–050. Do not start those until the rule is written, or they will each invent
  their own and the phase produces four conventions instead of one.
- If applying the rule to `edge_dashboard.py` reveals the rule is wrong, **change the rule and say
  so in PROGRESS.md.** That is the point of proving it on a small page first. A convention written
  once and never tested against real code is how `components/` came to be empty in the first place.
