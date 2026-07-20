# 030 — Extract test_signal's service layer

**Status:** not started
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
