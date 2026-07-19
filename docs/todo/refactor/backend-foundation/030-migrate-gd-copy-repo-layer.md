# 030 — Migrate gd_copy_signal's data layer onto the new repo/adapter

**Status:** not started
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
