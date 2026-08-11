# 020 — Test layout: retire the legacy limbo, fix the fixtures

**Status:** not started
**Depends on:** none (but sequence after phase3/010 deletions to avoid moving dead tests)
**Touches money:** no
**Layer:** tools/tests
**Leverage:** the documented layout in docs/system/rules/40-testing.md is the target — this task makes the
tree match the doc, not the reverse

## Problem

Review testing M6/M7: 124 of 180 test files live in `tests/core/`, documented as "legacy, closed";
`tests/reversal_engine/` lacks `__init__.py` while duplicate basenames exist across sibling dirs
(collection-order accidents waiting); `frontend/tests/` is an empty decoy package still listed in
`testpaths` while real frontend tests live in `tests/frontend/`; `fresh_db` is defined locally 118
times in 17 variants, each poking DB privates its own way; `test_pages_render.py` globs `*.py`
only, missing the `frontend/pages/trading/` package entirely.

## Decision

Move tests/core files to their by-area homes (mirroring `services/<area>`) in mechanical,
suite-green commits; add the missing `__init__.py`s; delete the `frontend/tests/` decoy and its
testpaths entry; promote one canonical `fresh_db` fixture to `tests/conftest.py` (built on the
phase2/050 connection factory) and migrate the 118 local copies; fix the pages-render glob to walk
packages.

## What must NOT change

- Test *content*: assertions move verbatim; any test that fails after a move was
  order/state-dependent — that's a real find, fix the dependency, never the assertion.
- Total selected-test count: identical before/after each move commit (paste the collection counts).
- Coverage numbers: within noise; floors untouched.

## Tests first (TDD)

- `tests/refactor/test_layout.py::test_no_files_under_tests_core` — drains to green as the move
  completes — structural
- `::test_all_test_dirs_are_packages` — `__init__.py` everywhere; negative control: temp dir
  without one fails — structural + control
- `::test_no_duplicate_test_basenames` — the collision class killed — structural
- `::test_fresh_db_defined_once` — AST count of fixture definitions == 1 — structural
- `test_pages_render` gains `::test_glob_includes_package_pages` — the trading/ pages render too —
  the gap the review found — surface

## What to do

1. Write the structural tests; confirm counts (124 files, 118 fixtures) — failing for the right
   reason is calibration here.
2. Canonical `fresh_db` first (so moved files can adopt it as they move).
3. Move by area, one commit each, collection-count receipts in PROGRESS.md.
4. Decoy deletion, testpaths, `__init__.py`s, glob fix.
5. `python -m tools.checks all` per commit.

## Where

- `tests/` tree, `tests/conftest.py`, `pyproject.toml`/pytest config (`testpaths`)

## Acceptance

- `tests/core/` empty and removed; one `fresh_db`; identical test counts; suite green at every
  commit.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Expect a handful of order-dependent tests to surface — budget for them; they are the payoff, not
  the obstacle.
