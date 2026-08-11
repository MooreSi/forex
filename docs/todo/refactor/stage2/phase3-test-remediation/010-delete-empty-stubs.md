# 010 — Delete the 13 assert-nothing characterization stubs

**Status:** not started · **Touches money:** no · **Layer:** tests
**Leverage:** the test-design review lists the 13 files; each has a populated `_surface` twin.

## Problem

13 characterization files in `tests/core/` (~1,536 LOC) were gutted — module docstring, `fresh_db`,
`_FakeBridge`, helpers, but **zero `def test_`**. They read as coverage while asserting nothing — the
exact "green without information" failure the golden rules name. Behaviour is safe (every one has a
populated `*_surface.py` twin that does test the extracted code), so these are dead scaffolding.

## Tests first (TDD)

- `tests/refactor/test_no_empty_test_files.py::test_every_test_file_has_a_test` — AST scan of tests/:
  any `test_*.py` with zero `def test_`/`async def test_` fails — structural
- `::test_detector_can_fail` — negative control: a temp `test_x.py` with only a docstring is flagged —
  control

(This gate replaces the manual list with an enforced rule so the class can't return.)

## What to do

1. Write the AST gate; run it — it flags the 13 (calibration).
2. For each, confirm its `_surface` twin exists and covers the behaviour (the review names them);
   `git rm` the empty stub. Cite each twin in the commit.
3. Run the gate → green; `python -m tools.checks all`.

## Where
- the 13 `tests/core/test_*_characterization.py` stubs (from the review) · `tests/refactor/test_no_empty_test_files.py` (new gate).

## Acceptance
- Zero `def test_`-free files under tests/; the new gate enforces it with a negative control; each
  deletion's twin named. Green suite.
