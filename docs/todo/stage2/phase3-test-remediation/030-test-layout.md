# 030 — Test-layout consolidation

**Status:** not started · **Depends on:** 010 (don't move the stubs — delete them first) · **Touches money:** no · **Layer:** tests

## Problem

Off-protocol layout (test-design review): 124 files in "closed" `tests/core/`; `tests/services/` flat
with no service mirror; `tests/reversal_engine/` missing `__init__.py` (shares 3 basenames with
siblings → collection-order hazard); `frontend/tests/` a ghost still in `testpaths`; `test_engine.py`
mutates `os.environ`/`sys.path`/`db.init()` at import time (unsafe under xdist).

## Tests first (TDD)

- `tests/refactor/test_layout.py::test_all_test_dirs_are_packages` — every test dir has `__init__.py`
  (+ negative control) — structural
- `::test_no_duplicate_basenames_without_packages` — the collision class killed — structural
- `::test_testpaths_has_no_ghost_dir` — every `testpaths` entry exists and is non-empty — structural
- `::test_no_import_time_env_or_db_mutation` — `test_engine.py` (and peers) do no import-time
  `os.environ`/`db.init` mutation (AST) — structural (+ negative control)

## What to do

1. Write the structural tests; confirm they fail on today's tree (calibration).
2. Add missing `__init__.py`; drop the `frontend/tests` ghost from pytest `testpaths`; move
   `test_engine.py`'s import-time mutation into a fixture. Move by-area where cheap (retiring
   tests/core is larger — do the safe wins now, note the bulk move for a follow-up).
3. Keep selected-test counts identical across each move (paste receipts). `python -m tools.checks all`.

## Where
- `tests/` tree · `pyproject.toml` testpaths · `tests/test_engine.py`.

## Acceptance
- Packages everywhere, no ghost testpaths, no import-time mutation, no duplicate-basename collisions;
  counts preserved. Green suite.
