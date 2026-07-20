# 020 — Extract TP trigger tracking

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract into `core_tp_trigger_tracking.py`. `_last_closed_tp`, `_check_sl`, `_get_remaining_lots`
become plain functions. `_get_triggered_tps`/`_log_tp_wait_diagnostic` need cross-call memory
that isn't in the DB (TTL cache, per-trade log-throttle timestamps) -- add one small `TPCache`
class (`triggered: dict`, `wait_log_ts: dict`), same pattern as pack 4's `DPMCache`.
`_check_tp_hits` takes a `TPCache` too, since it calls `get_triggered_tps` internally.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, `SimulationEngine.__new__`
  instance swapped for a plain `TPCache`, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_tp_trigger_tracking.py`: `TPCache` class, then `get_triggered_tps(cache,
   trade_id)`, `last_closed_tp(trade_id)`, `log_tp_wait_diagnostic(cache, trade_id, tag,
   direction, current_price, target_price, hit)`, `check_sl(trade, tick)`, `check_tp_hits(cache,
   trade, tick)`, `get_remaining_lots(trade_id)` -- 1:1 logic ports.
3. Re-run 010's suite against the new functions -- zero assertion changes (beyond the
   engine-instance -> `TPCache` swap).
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.

## Notes

Created `forex_trader/core/core_tp_trigger_tracking.py` (139 lines, well under the 800-line
ceiling) -- `TPCache` class plus 1:1 ports of all 6 functions, no logic changes.
`get_triggered_tps`/`log_tp_wait_diagnostic`/`check_tp_hits` take a `TPCache` instance instead
of implicit `self` state. Added `tests/core/test_tp_trigger_tracking_surface.py` (19 tests,
010's exact assertions re-pointed at the new module, the `SimulationEngine.__new__()` instance
replaced by a plain `TPCache()`, the db-worker-thread reset helper from 010 reused unchanged).
Full `tests/core/` suite: 200/200 green (181 from packs 1-4 + 19 from this pack). Repo-wide:
531/533 green -- same 2 pre-existing `pytest-asyncio`-missing failures from earlier packs,
unrelated. `engine.py` untouched -- new module not yet wired back in.
