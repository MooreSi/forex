# 020 — Migrate breakout_signal's data layer onto the shared adapter

**Status:** not started
**Depends on:** 010-characterize-breakout-current-behavior.md
**Real-money surface:** no
**Leverage:** `forex_trader/src/db/adapter.py` (already built), 010's characterization suite

## Problem

`close_signal()` and `book_partial_close()` have the same non-atomic multi-connection pattern
as `gd_copy_signal/database.py` had. Additionally, `engine.py` bypasses `database.py`'s API
entirely in three places: the level-cooldown check, the consecutive-loss check, and the TP2
stop-loss trail (which has no named function at all today).

## Decision

Structural port to `breakout_signal_repo.py`, same as `gd_copy_signal_repo.py`: every function
from `database.py`, using `DbAdapter` instead of raw `sqlite3`, with `close_signal` and
`book_partial_close` wrapped in `transaction()`. Add three new named functions to replace the
raw-SQL bypasses: `get_last_signal_time_for_level(direction, level, cutoff)`,
`get_recent_outcomes_by_direction(direction, since_ts, limit)` (same shape as gd_copy_signal's),
and `set_stop_loss(signal_id, price)` (net new — didn't exist before).

## Tests first (TDD)

- 010's suite, re-pointed at `breakout_signal_repo.py` via the same fixture-parametrization
  pattern used in `test_database_characterization.py` for gd_copy_signal (zero assertion
  changes).
- `tests/breakout_signal/test_repo_transactions.py` — same shape as gd_copy_signal's: forced
  mid-write failure in `close_signal`/`book_partial_close`, asserts atomic rollback.
- New tests for the three new named functions.

## What to do

1. Confirm 010's suite is green against current `database.py`.
2. Create `breakout_signal_repo.py`, port every function, add the three new ones.
3. Wrap `close_signal`/`book_partial_close` in `transaction()`.
4. Re-run 010's suite against the new module — zero assertion changes, must pass.
5. Add and pass the new tests.
6. Leave `database.py` in place, untouched.

## Where

- `forex_trader/breakout_signal/breakout_signal_repo.py` (new)
- `tests/breakout_signal/test_repo_transactions.py` (new)

## Acceptance

- 010's full suite passes against the new repo unmodified.
- Atomicity proven via forced-failure tests.
- `database.py` untouched.

## Notes

Same "don't delete the old file yet" rule as gd_copy_signal — cutover happens (if ever) in a
later pack once the app is actually wired to use these new modules.
