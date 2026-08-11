# 010 — Numbered migration runner + registry

**Status:** not started · **Touches money:** no (schema of money tables — care) · **Layer:** repo/db
**Leverage:** review-august-08 phase2/020 already added `db/migrations.py` with `apply_migration`
(fail-closed), `schema_version` stamp + `verify_critical_schema`. This adds the ORDERED, numbered
structure on top.

## Problem

The ~90 `ADD COLUMN`/`CREATE` statements still live inline in `database.py._apply_schema` as one flat
loop. Owner note: "Proper migrations, not all in the database.py." There is a `schema_version` stamp
but no per-step versioning — you can't tell which migrations a given DB has, or add one in order.

## Decision

Move the migration list into `db/migrations.py` as an ordered registry: `MIGRATIONS = [(1, fn), (2,
fn), ...]` (or numbered SQL steps), each idempotent, applied in order, advancing `schema_version` per
step. `_apply_schema` becomes: create tables, then `migrations.run(conn)`. Keep the fail-closed
handling (skip duplicate-column, abort on real error) already built.

## What must NOT change

- No schema/table/column is renamed or dropped — mechanism only, shape frozen (phase2/020's pre-flight
  check catches drift).
- Existing installed DBs upgrade losslessly; a fresh DB reaches the same head as today.
- `busy_timeout`/WAL/backup behaviour untouched.

## Tests first (TDD)

- `tests/db/test_migration_registry.py::test_steps_apply_in_order_and_advance_version` — each step
  bumps schema_version; head == len(MIGRATIONS) — behaviour
- `::test_rerun_is_idempotent` — running twice applies once (all duplicate-column skips) — regression
- `::test_registry_matches_schema` — after run, `verify_critical_schema` passes; the columns the old
  flat loop added are all present — behaviour (parity with today)
- `::test_bad_step_aborts` — a planted failing step aborts startup (fail closed) — control

## What to do

1. Write the tests; watch them fail.
2. Build the ordered registry in `db/migrations.py`; transcribe the `_apply_schema` ALTER list into
   numbered steps (verbatim SQL). Add `run(conn)` that applies pending steps in order via the existing
   `apply_migration`, advancing `schema_version`.
3. Replace the inline loop in `database.py` with `migrations.run(conn)`.
4. `python -m tools.checks all`.

## Where
- `backend/src/db/migrations.py` — the registry + runner · `backend/src/db/database.py` — call it.

## Acceptance
- The ALTER list is ordered, numbered, out of database.py; a fresh DB and a real/legacy DB reach head;
  rerun is a no-op; a bad step aborts. Green suite. (Legacy-shape proof is task 020.)
