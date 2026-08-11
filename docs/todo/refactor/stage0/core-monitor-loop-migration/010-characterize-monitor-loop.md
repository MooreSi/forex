# 010 — Characterize monitor loop's real-logic blocks

**Status:** Done (2026-07-20)
**Depends on:** none (reuses `core_close_trade`/`core_partial_close`,
both already extracted and independently characterized)
**Real-money surface:** `reconcile_sl_hit` and `check_profit_close_target`
can close a real MT5 position (`bridge.close_position`) or record a
partial close -- both call the same real close/partial-close collaborators
the original code called, faked in every test here.

## Decision

None of the four target pieces exist as separate original methods except
`_check_sl` -- `reconcile_sl_hit`/`check_profit_close_target`/
`reclaim_ea_managed_trade` are inline blocks inside `_monitor_loop` itself,
so characterization drives the whole loop for exactly one iteration (via
the established `asyncio.sleep`-stops-`_monitor_running` technique) with a
real DB-backed open trade and a fake bridge/tick engineered to hit the
specific block under test, with every OTHER collaborator
(`_record_close`/`partial_close_trade`/`_schedule_profit_sync`/
`_background_close_commentary`/`_handle_scale_out`/`ea_bridge.get_instance`)
faked so each test isolates one block's own logic.

Every branch pre-traced via throwaway scripts first, given the number of
interacting gates and the fact that these blocks had never been
independently tested before.

## Tests first (TDD)

- `tests/core/test_monitor_loop_characterization.py`:
  - `_check_sl`: BUY crosses (bid<=SL) / SELL crosses (ask>=SL) / no cross
    / no SL set.
  - SL hit, MT5 still shows the full position open (broker's own SL hasn't
    fired yet) -> deferred, no partial/full close recorded.
  - SL hit, MT5 shows a smaller live volume (broker already partially
    closed it) -> `partial_close_trade` called with the closed lots and the
    `MT5_<reason>` reason, using the crossing price (not the current tick).
  - SL hit, ticket no longer in MT5's live positions at all -> full local
    close, `_schedule_profit_sync`/`_background_close_commentary` both
    fired.
  - SL hit, bridge not configured -> MT5 check skipped entirely, straight
    to full local close.
  - SL hit, `get_positions()` raises -> caught, falls through to full
    local close (same as bridge-not-configured).
  - SL hit, no `mt5_ticket` -> full local close, but
    `_schedule_profit_sync` is NOT fired (guarded by `if mt5_ticket:`).
  - Profit-close target reached, MT5 close succeeds -> closes at MT5's own
    reported close price.
  - Profit-close target NOT reached -> no close, falls through to strategy
    handler dispatch.
  - `profit_close_usd` is `0`/unset (disabled) -> no check at all, falls
    through to dispatch.
  - Profit-close target reached, MT5 close rejected (`{"success": False}`)
    or raises -> falls back to the current tick price for the local close
    either way.
  - EA-managed trade, EA instance healthy -> skipped entirely for the
    cycle (no reclaim, no dispatch).
  - EA-managed trade, EA unhealthy -> reclaimed (`managed_by` flipped to
    `'python'` in the DB, one alert sent), THEN falls through to strategy
    handler dispatch in the same cycle.
  - EA-managed trade, EA instance is `None` -> same reclaim-and-dispatch
    behavior as unhealthy.

## What to do

1. Write the test file using a fake bridge, a real DB-backed open trade
   per scenario, and faked collaborators, calling `_monitor_loop` via
   `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- every
  order-placing collaborator (`close_position`, `partial_close_trade`,
  `_record_close`) is always faked.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

15 tests written in `tests/core/test_monitor_loop_characterization.py`,
all green on the first run against unmodified `engine.py` after fixing the
same missing-`self`-parameter mock issue seen in several prior packs when
faking methods directly on the class. No `engine.py` bugs found in any of
the four blocks.
