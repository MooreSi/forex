# 030 — Migrate gd_copy_signal's data layer onto the new repo/adapter

**Status:** Done (2026-07-19)
**Depends on:** 010-data-access-foundation.md, 020-characterize-gd-copy-current-behavior.md
**Real-money surface:** no
**Leverage:** `forex_trader/src/db/adapter.py` (010), 020's characterization suite as the
behavior-equivalence check

## Problem

`gd_copy_signal/database.py`'s `close_signal()` and `book_partial_close()` each perform
multiple related writes across separate `with _conn()` blocks — not atomic. A crash between
them leaves the signal record and the balance ledger inconsistent, with no automatic recovery.

## Decision

Rebuild the data-access layer as `gd_copy_signal_repo.py` on top of the new `DbAdapter` (010),
wrapping `close_signal`'s and `book_partial_close`'s multi-statement sequences in single
`transaction()` blocks. Keep the schema and every function signature behavior-identical to
today — 020's tests are the contract. This task is a structural migration, not a behavior
change. Money-as-float (the `REAL` columns) stays as-is here; that's deferred to a later pack
(QUESTIONS.md #10) since fixing it ripples into the UI, sync protocol, and Telegram alerts.

## Tests first (TDD)

- 020's existing characterization suite, re-pointed at the new `gd_copy_signal_repo.py` —
  must pass with zero modifications to its assertions (proves behavior equivalence).
- `tests/gd_copy_signal/test_repo_transactions.py` — new test asserting `close_signal`'s
  status-update and balance-update now happen atomically: force an exception between the two
  statements and assert BOTH roll back. (Not meaningfully testable against the old
  two-transaction code — that's exactly why this is worth doing.)

## What to do

1. Confirm 020's suite is green against current `database.py` (prerequisite check).
2. Create `gd_copy_signal_repo.py` implementing every function currently in `database.py`,
   using `DbAdapter` instead of raw `sqlite3`.
3. Wrap `close_signal`'s and `book_partial_close`'s multi-statement sequences in
   `transaction()` blocks.
4. Re-run 020's full suite against the new repo module — must pass unchanged.
5. Add and pass `test_repo_transactions.py`.
6. Leave `database.py` in place, untouched, until 040 confirms the new repo is wired in
   end-to-end — avoids a half-migrated state where some code reads/writes through the old
   module and some through the new one.

## Where

- `forex_trader/gd_copy_signal/gd_copy_signal_repo.py` (new)
- `tests/gd_copy_signal/test_repo_transactions.py` (new)

## Acceptance

- 020's full characterization suite passes against `gd_copy_signal_repo.py` with zero
  modifications to the test assertions.
- `test_repo_transactions.py` demonstrates atomic rollback on `close_signal`'s two-statement
  sequence.
- `database.py` is untouched — this repo is a parallel replacement until 040 cuts over, not an
  in-place edit.

## Notes

Don't delete or edit `database.py` in this task. 040 is where the cutover happens, once the
service layer is also ready.

**Bug found and fixed while implementing (2026-07-19):** `create_signal`'s `INSERT OR IGNORE`
on a duplicate `signal_ref` returned the *previous* successful insert's `lastrowid` instead of
`0`. Root cause: `database.py` opens a fresh `sqlite3.connect()` per call, so `cursor.lastrowid`
on a no-op insert is naturally `None` on a connection that's never inserted anything; the new
adapter reuses one persistent connection, so `lastrowid` is connection-level state that
survives a no-op write. Caught immediately by 020's parametrized characterization suite (same
test, same assertion, run against both backends) — exactly the scenario this suite exists for.
Fixed in `SqliteAdapter.run()` by gating `lastrowid` on `rowcount > 0`; added a direct
regression test to 010's own `test_adapter.py` so it's covered independent of `gd_copy_signal`.

020's test file (`test_database_characterization.py`) was also lightly restructured (fixture
only, no assertion changes) to parametrize `fresh_db` over both `database` and
`gd_copy_signal_repo`, so the same 38 assertions run against both backends without duplication.
Two tests that depended on private internals (`database._DB_PATH`, `database._conn()`) were
rewritten to use only the public API, so they work identically against either backend — a
strict improvement to the suite's own robustness, not a behavior-scope change.

`test_repo_transactions.py` (3 tests) proves the atomicity fix directly: forces a mid-write
failure inside `close_signal`/`book_partial_close` and asserts both statements roll back
together, which `database.py`'s independent-connections version cannot do correctly.

Total: 111 tests passing (38 database.py assertions x 2 backends = 76, plus 21 engine, 11
adapter/connection from 010 with the new regression test, and 3 repo-transaction tests = 111).
