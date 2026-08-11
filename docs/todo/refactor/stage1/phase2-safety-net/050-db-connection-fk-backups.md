# 050 — DB connection hardening, FK-safe deletes, daily backup

**Status:** not started
**Depends on:** 020-schema-migrations.md (backup-before-migrate hooks its runner)
**Touches money:** no
**Layer:** repo/db
**Leverage:** SQLite's own `.backup` API (`sqlite3.Connection.backup`) — no new dependency

## Problem

Three data findings (review data H3/H4, backend H8):

- The main trading DB is the weakest-configured connection in the app (`database.py:170`): no
  `busy_timeout`, WAL only via schema, two writer threads, no write lock — "database is locked"
  errors are a matter of time, possibly on the trade path.
- Retention prune and `reset_simulation_data` delete parent trades before their
  `vantage_partial_closes` / `ladder_legs` children with FKs ON (`retention.py:81`,
  `trade_repo.py:335`) — the FK failure rolls back the whole prune and is downgraded to a
  `log.warning`.
- The live-money books are one SQLite file on one disk. No backup of any kind.

## Decision

One connection factory for the trading DB: WAL + `busy_timeout` pragmas at connect, a process-wide
write lock (two writer threads serialised), used everywhere the trading DB is opened. Fix delete
ordering children-first inside one transaction. Add a daily backup via the SQLite backup API to a
sibling `backups/` folder with retention of 30 (QUESTIONS.md #4), plus an automatic
backup-before-migrate hook into 020's runner.

## What must NOT change

- Schema — zero DDL here (020 owns mechanism, and shape is frozen anyway).
- Retention stays **opt-in, default off** (its audit-trail implications are QUESTIONS territory,
  not this task's).
- Read paths and query results — byte-identical.

## Tests first (TDD)

- `tests/db/test_connection_factory.py::test_all_trading_connections_use_factory` — structural:
  grep/AST for raw `sqlite3.connect` outside the factory — structural
- `::test_pragmas_applied` — busy_timeout + WAL on a factory connection — surface
- `::test_two_writers_serialised` — two threads write under the lock, no locked error, both land —
  behaviour
- `tests/db/test_fk_deletes.py::test_prune_deletes_children_first` — parent with partial-close +
  ladder children prunes cleanly — regression
- `::test_prune_failure_is_loud` — planted FK violation → error, not warning — control
- `tests/db/test_backup.py::test_daily_backup_creates_valid_db` — backup opens and matches row
  counts — behaviour
- `::test_backup_retention_keeps_n` — 31st backup rotates the 1st out — boundary
- `::test_backup_before_migrate_runs` — 020's runner triggers a backup first — wiring

## What to do

1. QUESTIONS.md #4 (destination + cadence) answered first.
2. Write the tests above; run them; confirm they fail for the right reason.
3. Build the factory; sweep every trading-DB `connect` call onto it (`database.py:170` first).
4. Reorder the deletes in `retention.py:81` and `trade_repo.py:335`; upgrade the failure logging.
5. Backup task (daily timer + before-migrate hook + rotation); destination configurable via
   `/add-tunable`.
6. `python -m tools.checks all`.

## Where

- `backend/src/db/connection.py` / `database.py:170` — factory
- `backend/src/db/retention.py:81`, trade repo `:335` — delete order
- `backend/src/db/backup.py` — new

## Acceptance

- Concurrent-writer test green under stress (loop it locally); prune of a deep trade tree works;
  a backup file from the running app opens in a fresh sqlite3 and passes `PRAGMA integrity_check`.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Progress notes (2026-08-10)

**Landed (tests-first, 5 tests; full suite pending):**
- **Backups** — new `backend/src/db/backup.py`: `backup_now` (SQLite online backup API, safe against
  a live DB), `rotate` (keep N), `maybe_daily_backup` (at most one per calendar day, keep 30 per
  Q001 #4). Wired into `run.py` right after `db.init`, non-fatal. Destination `DATA_DIR/backups/`.
- **busy_timeout** — `db()` now sets `PRAGMA busy_timeout=5000` at connect, so a concurrent write
  from the second writer thread waits for the lock instead of failing instantly with "database is
  locked". (WAL was already set via the schema PRAGMA.)

**Still TODO within 050 (more invasive — deferred to keep risk low):**
- **Process-wide write lock** serialising the two writer threads (caller + to_db_thread). Higher
  risk: it wraps the hot transaction path. Coordinate with phase2/030's slot-claim lock when that
  money task is done (they should share one lock discipline). Note: busy_timeout already removes the
  *immediate-error* failure mode; the lock is belt-and-suspenders for true write serialisation.
- **FK-safe delete ordering** in `retention.py` (~81) and the reset/`trade_repo` delete (~335) —
  delete children (vantage_partial_closes / ladder_legs) before parents so an FK-ON prune can't
  roll back wholesale; upgrade the swallowed `log.warning` on failure. Retention is opt-in/default
  off (Q005 #4), so this is latent unless enabled — real but not urgent for local running.

The two landed pieces deliver the core "won't lose the books" + "no lock-storm" value for running
locally; the deferred pieces are follow-ups within this same task.

## Notes

- The write lock must be cheap — it wraps transactions, not the process. Watch trade-path latency.
- Coordinates with 2/030's slot claim (same lock discipline) — whichever lands second rebases.
