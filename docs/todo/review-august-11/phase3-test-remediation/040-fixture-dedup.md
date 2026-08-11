# 040 — Consolidate fresh_db and _FakeBridge fixtures

**Status:** not started · **Depends on:** 010, 030 · **Touches money:** no (tests; the fake must stay MT5-safe) · **Layer:** tests

## Problem

`fresh_db` is redefined locally in ~115 files (17 variants), `_FakeBridge` in ~69 (was ~40). This
sprawl means DB-internal changes break dozens of files at once, and the ad-hoc fakes risk drifting
from the real bridge surface. Phase-5's `FakeMT5Bridge` (a proper, surface-matched fake) should become
the one fake the tests share.

## Tests first (TDD)

- `tests/refactor/test_fixture_dedup.py::test_fresh_db_defined_once` — AST count of `fresh_db`
  definitions trends to 1 (canonical conftest); enforce a shrinking baseline that reaches 1 — structural
- `::test_no_adhoc_fakebridge_when_shared_exists` — once phase-5 lands FakeMT5Bridge, new files use it;
  count of local `_FakeBridge` classes shrinks (baseline) — structural
- MT5 safety unchanged: `::test_no_test_imports_metatrader5` stays green — control

## What to do

1. Canonical `fresh_db` already exists in `tests/conftest.py` — migrate local copies to it file by
   file, diffing each (the 17 variants are not all interchangeable — read before deleting).
2. After phase-5, point ad-hoc `_FakeBridge` uses at the shared `FakeMT5Bridge`.
3. Enforce with a shrinking baseline (never rising). `python -m tools.checks all` per batch.

## Where
- `tests/conftest.py` (canonical) · the ~115 + ~69 local definitions.

## Acceptance
- `fresh_db` defined once; ad-hoc fakes shrinking toward the shared one; MT5-safety intact; counts
  preserved per move. Green suite.
