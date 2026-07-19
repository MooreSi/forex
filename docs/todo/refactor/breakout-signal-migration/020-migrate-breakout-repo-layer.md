# 020 — Migrate breakout_signal's data layer onto the shared adapter

**Status:** Done (2026-07-19)
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

**Important: the known `close_signal` double-counting bug (see 010's notes) was preserved
faithfully, NOT fixed.** `breakout_signal_repo.py`'s `close_signal` applies `balance_delta =
net_pnl_dollars` exactly like `database.py` does — the transaction wrapper only fixes
atomicity (the read-compute-write sequence being interrupted), which is a separate concern from
what value gets computed. Confirmed via the parametrized suite: the killer test's bug-preserving
assertion (`balance == 1055.0`, not the naively-expected `1032.0`/`1079.66`) passes identically
against both `database` and `repo`.

`test_engine_characterization.py`'s fixture still inits via `database`, not `repo` — `engine.py`
itself hasn't been repointed yet (that's 030), so its internal `bdb` reference is still bound to
the old module. Repointing the test fixture prematurely would have silently tested against the
wrong backend; caught this before it shipped.

88 tests total (39 database tests × 2 backends, plus engine and repo-transaction/new-function
tests). All green. `database.py` untouched.
