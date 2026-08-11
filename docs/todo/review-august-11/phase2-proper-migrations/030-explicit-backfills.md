# 030 — Make the data backfills explicit (retire except-pass)

**Status:** not started · **Depends on:** 010 · **Touches money:** no (data cleanup, not schema) · **Layer:** repo/db

## Problem

Beyond the ADD-COLUMN loop, `_apply_schema` has several one-off data backfills (rebrand renames,
`instant:` prefix stripping, order_type backfill) each wrapped in its own `except Exception: pass`
(database.py ~952-1024). Like the schema loop before phase2/020, these can swallow a real failure.

## Tests first (TDD)

- `tests/db/test_backfills.py::test_each_backfill_applies_on_legacy_data` — seed pre-backfill rows,
  run, assert the rows are corrected — behaviour (one test per backfill)
- `::test_backfill_failure_is_not_swallowed` — a planted failure surfaces (log at error / abort per
  policy), not silent pass — control
- `::test_backfills_are_idempotent` — rerun changes nothing — regression

## What to do

1. Write the tests; watch them fail.
2. Move the backfills into named, tested steps (in the registry as data-migration steps, or a sibling
   `db/backfills.py`); replace `except: pass` with the phase2/020 policy (skip only benign, surface
   real errors).
3. `python -m tools.checks all`.

## Where
- `backend/src/db/migrations.py` (data steps) or `backend/src/db/backfills.py` · database.py call site.

## Acceptance
- No `except Exception: pass` remains in the schema/backfill path; each backfill is named, idempotent,
  tested, and fails loud on a real error. Green suite.
