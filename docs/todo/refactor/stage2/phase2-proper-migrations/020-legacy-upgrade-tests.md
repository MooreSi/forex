# 020 — Legacy-DB upgrade fixtures & tests

**Status:** not started · **Depends on:** 010 · **Touches money:** no · **Layer:** tests/db

## Problem

We assert migrations reach "head" on a fresh DB, but the risk is real *installed* DBs — created by
older schema versions — upgrading in place. Without fixtures for those historical shapes, a broken
upgrade is invisible until it hits a user's live-money DB.

## Tests first (TDD)

- `tests/db/test_legacy_upgrade.py::test_legacy_shapes_reach_head` — build ≥3 realistic pre-migration
  DB snapshots in-test (a base-schema-only DB; one missing a mid-history column set; one at an
  intermediate version), run `migrations.run`, assert each reaches head with all critical columns and
  row counts preserved — behaviour
- `::test_upgrade_is_lossless` — seed rows before upgrade; assert identical rows after — boundary
- `::test_detector_can_fail` — negative control: a fixture deliberately missing a column that a step
  should add fails until the step runs — control

## What to do

1. Write the fixtures (create old-shape tables via raw sqlite3), then the tests; watch them fail if
   the runner is incomplete.
2. Fix any gaps the fixtures reveal in the registry (task 010).
3. `python -m tools.checks all`.

## Where
- `tests/db/test_legacy_upgrade.py` (new) · fixtures inline or `tests/db/fixtures/`.

## Acceptance
- Each historical shape upgrades to head losslessly; the negative control proves the tests can fail.
  Green suite.
