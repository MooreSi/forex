# 040 — Never record a DB close the broker refused

**Status:** not started
**Depends on:** none (ships with 030 — its flagged-open leftovers need the reconciler to settle)
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
**Layer:** service
**Leverage:** frozen-path wrappers `backend/src/runtime.py:420-506`

## Problem

`positions/monitor_loop.py:128` runs `record_close` even when the broker close failed or raised
(review backend Critical #3, risk H1) — the DB says closed while MT5 says open, and the failure is
logged at debug so nobody sees it. The profit-close and SL-reconcile paths in `monitor_loop.py` are
younger near-copies of the frozen close path without its safeguards, and the SL-reconcile variant
skips ladder-leg closing (orphans Adaptive Runner legs — risk H2).

## Decision

Make `record_close` in the monitor loop conditional on a *confirmed* broker close result; on
failure/exception: log at **error**, notify, leave the DB open for reconciliation (030) to settle.
Where monitor_loop near-copies the frozen path, replace the copy with a call to the runtime
wrappers. Chosen over "fix the copies in place" because the copies existing at all is the defect —
the frozen path is frozen precisely so there is one close implementation.

## What must NOT change

- The frozen close path itself (`close_trade`, `record_close`, `_make_close_trade_ctx`,
  `partial_close_trade`) — zero edits. This task changes *callers* only.
- Close-path witness tests pass unmodified.
- Profit-close/SL-reconcile *trigger conditions* (when a close is attempted) — byte-identical;
  only what happens after the broker responds changes.

## Tests first (TDD)

- `tests/positions/test_monitor_close_recording.py::test_failed_broker_close_records_nothing` —
  fake broker returns failure retcode → no DB close row, error log emitted — regression
- `::test_close_exception_leaves_db_open` — fake broker raises → DB open, error log — regression
- `::test_successful_close_still_records` — negative control: confirmed close → exactly one DB
  close via the runtime wrapper — control
- `::test_monitor_close_routes_through_frozen_wrapper` — structural: monitor_loop no longer
  contains its own close-recording sequence (assert the near-copy is gone AND that the detector
  finds a planted copy) — structural + control
- `::test_sl_reconcile_close_includes_ladder_legs` — fake position with ladder legs → legs closed
  with the parent, none orphaned — behaviour

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. In `monitor_loop.py`, gate every `record_close` on the broker result; failure → error-level log
   + notification + leave open.
3. Replace the profit-close and SL-reconcile close-recording near-copies with calls to the
   `runtime.py:420-506` wrappers (moving verbatim is allowed; reshaping the frozen functions is not).
4. Route ladder-leg closing through the same wrapper path so SL-reconcile can't orphan legs.
5. `python -m tools.checks all`.

## Where

- `backend/src/services/positions/monitor_loop.py` — the only file that changes behaviour

## Acceptance

- Grep shows `record_close` called from monitor_loop only behind a confirmed-close condition, via
  the runtime wrapper.
- **The killer test (demo session):** force a demo close rejection (e.g. wrong filling mode against
  demo); DB still shows the position open, an error alert fired, and reconciliation's next pass
  reports it consistent.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Related finding risk H5 (bridge close hardcodes ORDER_FILLING_IOC while opens document Vantage
  needs RETURN) is adjacent but separate — it makes close *failures more likely*, this task makes
  them *honest*. If trivial, fix the filling-mode fallback in the same demo session under the same
  sign-off; otherwise raise it as its own task. Decide with the owner at `/safe-change` time.
