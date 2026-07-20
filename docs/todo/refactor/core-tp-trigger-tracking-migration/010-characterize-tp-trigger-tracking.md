# 010 — Characterize TP trigger tracking

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same approach as packs 1-4's 010: characterize against the real `forex_trader.core.database`
module (`db_module`), using a temp file passed to `db_module.init()`.

## Tests first (TDD)

- `tests/core/test_tp_trigger_tracking_characterization.py`:
  - `_get_triggered_tps` — parses `TP<n>` reason strings from `vantage_partial_closes` into a
    `set[int]`; non-matching reasons ignored; 2.5s TTL cache returns the same (stale) set on a
    second call within the window even if the table changes underneath it; expires and
    re-queries after the TTL.
  - `_last_closed_tp` — returns the TP number of the most recent `lots_closed > 0` row; ignores
    zero-lot rows (e.g. a skipped/marker row); returns `None` when there's no match.
  - `_log_tp_wait_diagnostic` — no assertions on log output itself (logging, not app state);
    characterize only the throttle-timestamp bookkeeping via a fake/spy, OR skip detailed
    testing of this one (pure logging side effect, lowest value to characterize in detail) and
    just confirm it doesn't raise across the hit/not-hit and BUY/SELL branches.
  - `_check_sl` — BUY hit when `tick.bid <= sl`; SELL hit when `tick.ask >= sl`; `None` when no
    stop set or not hit.
  - `_check_tp_hits` — skips TPs already in the triggered set; skips a TP on the wrong side of
    entry (BUY TP <= entry, SELL TP >= entry); BUY hits when `tick.bid >= tp`; SELL hits when
    `tick.ask <= tp`; returns multiple simultaneous hits when several TP levels are crossed in
    one tick.
  - `_get_remaining_lots` — reads current `remaining_lots`; returns `0.0` for an unknown
    trade_id.

## What to do

1. Write the test file against `SimulationEngine`'s real methods. `_get_triggered_tps` and
   `_log_tp_wait_diagnostic` need a minimal engine stand-in exposing `_tp_cache`,
   `_tp_wait_log_ts` (same `_FakeEngine`-style pattern as pack 4). The other four need no
   `self`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from packs 1-4.

## Notes

19 tests written in `tests/core/test_tp_trigger_tracking_characterization.py`. Two real issues
found and fixed before the suite was trusted:

1. **Test design, not an engine.py bug**: `_check_tp_hits` calls `self._get_triggered_tps(...)`
   internally, so a bare `_FakeEngine` stand-in (this pack's first draft, mirroring pack 4's
   pattern) doesn't have that bound method. Fixed by switching to
   `SimulationEngine.__new__(SimulationEngine)` (pack 1's Risk Governor pattern) with
   `_tp_cache`/`_tp_wait_log_ts` set manually since `__init__` never runs.

2. **New, previously-undocumented DB fixture gotcha**: `_get_triggered_tps` is the first
   function in this whole migration series to go through `db_module.to_db_thread()`, which runs
   on `db._db_executor` -- a **persistent single-worker `ThreadPoolExecutor`**, not the calling
   thread. That worker thread has its own `threading.local()` storage, completely separate from
   the test thread's. The existing `_reset_thread_local_connection()` fixture helper (used
   unchanged by every prior pack) only resets the calling thread's cached connection -- it has
   zero effect on the worker thread's, so a "fresh" per-test temp DB was silently invisible to
   any `to_db_thread()`-routed call, which kept serving an earlier test's (already-deleted) file.
   Fixed with a new `_reset_db_worker_thread_connection()` helper that submits the reset
   function to run ON the worker thread via `db._db_executor.submit(...).result()`, called in
   fixture setup AND teardown alongside the existing main-thread reset. Any future pack whose
   characterized methods use `to_db_thread()` needs this too -- worth calling out prominently
   since it's easy to miss (tests can silently read/assert against stale data instead of failing
   loudly).

Confirmed `_get_triggered_tps`'s 2.5s TTL cache and `_check_tp_hits`'s "skip already-triggered /
skip wrong-side-of-entry" logic both behave as documented. No engine.py bugs found in this
cluster.
