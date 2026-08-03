# 010 — Data access foundation

**Status:** Done (2026-07-19)
**Depends on:** none
**Real-money surface:** no
**Leverage:** `database-conventions` skill's `DbAdapter` pattern (§1-3), translated from
TypeScript/`better-sqlite3` to Python/`sqlite3`

## Problem

No shared data-access foundation exists yet. Every engine opens raw `sqlite3` connections ad
hoc. `gd_copy_signal/database.py` already wraps each call in a context manager that
commits/rolls back a single connection (`_conn()`, lines 31-42), but there's no way to compose
multiple statements into one atomic transaction — `close_signal()` (database.py:332-352) does
the status update and the balance update as two separate `with _conn()` blocks. A crash
between them leaves the signal and the balance ledger disagreeing, with no recovery path.

## Decision

Build a small typed adapter — a `DbAdapter` protocol wrapping `sqlite3.Connection` — exposing
`get`, `all`, `run`, `exec`, and `transaction()` (a context manager for composing multiple
statements atomically), per `database-conventions` §1-3. This is the repo/adapter pattern
chosen over a traditional ORM (see QUESTIONS.md #2, answered). New code, no existing behavior
to characterize — pure TDD from the start.

## Tests first (TDD)

- `tests/refactor/db/test_adapter.py` — asserts `get()`/`all()`/`run()`/`exec()` work against
  an in-memory SQLite db; asserts `transaction()` commits multiple statements together, and
  rolls back ALL of them when an exception is raised mid-block. This last assertion is the
  behavior `close_signal()` lacks today — it's the actual point of this task.
- `tests/refactor/db/test_connection.py` — asserts `init_db(path)` creates a fresh adapter
  bound to that path, `get_db()` returns it, `set_db()` swaps it (for test isolation between
  test files), `close_db()` releases it cleanly.

## What to do

1. Write the tests above; run them; confirm they fail (no `src/db/` module exists yet).
2. Create `forex_trader/src/db/adapter.py` — the `DbAdapter` interface (`get`/`all`/`run`/
   `exec`/`transaction` signatures).
3. Create `forex_trader/src/db/sqlite_adapter.py` — `SqliteAdapter` implementing `DbAdapter`
   over `sqlite3.Connection`, WAL mode + `foreign_keys` pragma on connect.
4. Create `forex_trader/src/db/connection.py` — module-level `get_db`/`init_db`/`set_db`/
   `close_db`, generalizing the global-singleton pattern `gd_copy_signal/database.py` already
   uses (`_DB_PATH`).
5. Run the tests from step 1, confirm green.

## Where

- `forex_trader/src/db/adapter.py` (new)
- `forex_trader/src/db/sqlite_adapter.py` (new)
- `forex_trader/src/db/connection.py` (new)
- `tests/refactor/db/test_adapter.py` (new)
- `tests/refactor/db/test_connection.py` (new)

## Acceptance

- All new tests pass.
- **The killer test:** `transaction()` demonstrably rolls back a partial multi-statement write
  when an exception fires mid-block — the exact bug class `close_signal()` has today.
- No existing file outside this new `src/db/` addition is touched.

## Notes

This is the shared foundation 030 builds `gd_copy_signal_repo.py` on top of. Keep it
engine-agnostic — it isn't `gd_copy_signal`-specific, it's what future engine migrations reuse.
