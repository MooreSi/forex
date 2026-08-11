# Phase 2 — Proper migrations (out of database.py)

**Status:** not started — unblocked
**Gated on:** nothing (builds on review-august-08 phase2/020's fail-closed core, already landed)
**Touches money:** no (but it governs the schema of live-money tables — treat with care)

## Goal of this phase

Schema evolution becomes proper, ordered, versioned migrations in their own module — not ~90 ad-hoc
`ALTER`s living in `database.py`. Owner note (`docs/todo/notes.md`): *"Proper migrations, not all in
the database.py."* The Aug-08 work already made migrations **fail closed** (skip duplicate-column,
abort on real errors) and added a `schema_version` stamp + pre-flight check; this phase does the
structural refinement that was explicitly deferred there.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-migration-runner.md](010-migration-runner.md) | A numbered migration runner + registry in db/migrations.py; transcribe the ALTER list into ordered steps keyed by schema_version | no |
| [020-legacy-upgrade-tests.md](020-legacy-upgrade-tests.md) | Fixtures for real historical DB shapes; prove each upgrades to head losslessly | no |
| [030-explicit-backfills.md](030-explicit-backfills.md) | Move the remaining `except: pass` data backfills into the runner as explicit, tested steps | no |

## Exit criteria

- The ADD-COLUMN list lives as numbered steps in db/migrations.py, not inline in `_apply_schema`.
- `schema_version` advances per applied step; a fresh DB and each legacy-shape fixture both reach head.
- No `except Exception: pass` remains in the migration/backfill path (fail closed, tested).
- `python -m tools.checks all` green; boot smoke exercises the runner.
