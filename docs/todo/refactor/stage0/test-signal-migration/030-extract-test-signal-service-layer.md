# 030 — Extract test_signal's service layer

**Status:** Done (2026-07-20)
**Depends on:** 020
**Real-money surface:** no (connectivity only in this pack's scope, no MT5 connection in this task)

## Decision

Same mixin-composition pattern:
- `test_signal_service.py` — thin orchestrator: lifecycle (incl. the watchdog's self-healing
  `start()` re-entry logic, which is unique to this engine), `_cycle_loop`/`_run_cycle`,
  `_outcome_loop`'s routing, `_watchdog_loop`.
- `test_signal_manage.py` — `_close_signal`, the SL/TP1/TP3/time-stop ladder inside
  `_check_outcomes`, `_reconcile_live_pnl`, `_generate_learning_note`.
- `test_signal_velocity.py` — `_velocity_loop`/the velocity+sweep detection logic (more complex
  than breakout_signal's velocity loop — two independent detectors, not one).
- `test_signal_live_execute.py` — `_execute_live`.
- `test_signal_learn.py` — `_run_batch_analysis`.

## What to do

1. Confirm 010/020 suites green.
2. Extract in backend-conventions §7 order: learn -> velocity -> manage -> live_execute.
3. Reduce engine.py into test_signal_service.py.
4. Re-run 010's suite unmodified against the new structure.
5. Add test_service_surface.py.
6. Check external call sites BEFORE assuming anything can be deleted (same reminder as the last
   two packs — don't skip this check).

## Acceptance

- 010's suite passes unmodified.
- No new file over 800 lines.
- Killer test still passes end-to-end.

## Notes

Split into 6 files, not 5 -- the first cut of `test_signal_service.py` landed at 1,041 lines
(over budget), so `_run_cycle` (~550 lines alone) was pulled into a second-pass
`test_signal_generate.py` (_GenerateMixin). Final sizes: `test_signal_repo.py` 663,
`test_signal_generate.py` 638, `test_signal_manage.py` 384, `test_signal_service.py` 426,
`test_signal_velocity.py` 180, `test_signal_learn.py` 207, `test_signal_live_execute.py` 126 —
all comfortably under 800.

**Two real bugs caught and fixed during extraction, both before commit:**
1. `test_signal_velocity.py` and `test_signal_learn.py` initially imported the OLD `database`
   module instead of the new repo (same class of mistake as breakout_signal's 030) — caught by
   inspection this time, fixed immediately.
2. `_manage_triggered_signal`'s return value initially reused the ambient `sl_moved` flag to
   signal "did anything change this call" — but `sl_moved` stays `True` across every future
   cycle once TP1 has fired, so the caller's `notify_refresh()` would have fired on every
   outcome check indefinitely after TP1, not just the cycle TP1 actually moved. Fixed with a
   dedicated `tp1_moved_this_call` flag scoped to the call, caught before any test ran green
   against the wrong assumption.

**A third, more subtle one, also caught before commit:** the first draft of
`_manage_triggered_signal` used `asyncio.ensure_future()` (fire-and-forget) for its
`_close_signal()` calls instead of `await`. The original inline code in `_check_outcomes`
awaited each close sequentially before moving to the next open signal in the loop —
fire-and-forgetting would have let closes run concurrently/out-of-order, a real concurrency
behavior change this "no logic changes" extraction must not introduce silently. Fixed to
`await` directly, matching the other two engines' precedent.

**Integration gap found and fixed**: `ml_engine.py` (correctly out of scope, unmigrated)
imports the OLD `database` module directly in several functions (`record_outcome`,
`extract_features`, etc.) — before this task, `tdb` in `engine.py` *was* `database`, so one
`init()` call initialized both via the same module global. Now that the service's `tdb` is the
new repo, `test_signal_service.py`'s `init()` explicitly also calls the legacy
`database.init(db_path)` against the same file, so `ml_engine.py`'s independent dependency
keeps working. Test fixtures mirror this.

83 tests total, all green. Confirmed 8 external call sites (`ui/app.py`,
`ui/pages/remote_node.py`, `ui/pages/test_panel.py`, `core/app_lifecycle.py`,
`breakout_signal/engine.py`, `gd_copy_signal/gd_copy_signal_correlate.py`,
`gd_copy_signal/engine.py`, `sync/server.py` — plus `test_signal/adaptive_params.py` and
`test_signal/ml_engine.py` internally) — `engine.py`/`database.py` left in place, same
precedent as the other two engines.
