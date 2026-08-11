# 040 — Split database.py; retire the re-export hub

**Status:** not started
**Depends on:** phase2/020 (migrations already extracted the ALTER block — split what remains)
**Touches money:** no
**Layer:** repo/db
**Leverage:** `/split-file` (package-dir split preserving the import path); the import gates verify
the result

## Problem

`backend/src/db/database.py` is 1,251 lines wearing three hats (review backend H8, data #8): ~507
lines of schema, ~330 of migrations (gone after phase2/020), and a ~190-line hub re-exporting
100+ names from 17 service repos **upward** — with proven import-order fragility. The hub inverts
the dependency direction the architecture mandates: db must not know the services above it.

## Decision

`/split-file` the remainder into a `db/` package (schema, connection already separate, retention
already separate). Retire the re-export hub by mechanical sweep: every `from ...db.database import
X` where X belongs to a service repo becomes a direct import from that repo. Chosen over keeping a
deprecation shim forever because the hub's import-order fragility *is* the bug; a shim preserves
it.

## What must NOT change

- Every existing import site keeps working at each commit — the sweep is stepwise (hub shrinks as
  callers are rewired), never a big-bang break.
- Schema DDL text — byte-identical (phase2/020's pre-flight check would catch drift anyway).
- The four layer contracts stay at zero throughout.

## Tests first (TDD)

- `tests/refactor/test_db_hub_retired.py::test_no_service_names_reexported_from_db` — structural:
  db package exports no name defined under services/ — structural
- Negative control: planted re-export fails it — control
- `tests/refactor/test_import_order.py::test_db_imports_in_any_order` — import each db module in
  isolation (subprocess) — the fragility regression — structural
- The suite + boot smoke are the behaviour net; no behaviour changes.

## What to do

1. Write the structural tests; confirm the hub test fails against today's tree (it must — 100+
   names).
2. Sweep callers repo-by-repo (17 commits or grouped sensibly); shrink the hub each time.
3. Delete the hub section; `/split-file` what remains of database.py if still over 800 lines.
4. `python -m tools.checks all` after each commit.

## Where

- `backend/src/db/database.py` — shrinks/splits
- every `db.database` import site (grep-driven list, recorded in PROGRESS notes)

## Acceptance

- `database.py` (or its package) under 800 lines per file; hub gone; import-order test green;
  suite green throughout the sweep.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Do the sweep *after* phase3/010's deletions so nobody rewires imports of dead code.
