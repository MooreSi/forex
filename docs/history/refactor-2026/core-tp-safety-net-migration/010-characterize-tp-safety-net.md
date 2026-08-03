# 010 — Characterize TP safety net

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order's SL via `bridge.modify_order`
-- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs. `ea_bridge.get_instance()` is
faked -- real, external infrastructure, same treatment as `sync.server`/
`sync.client`. Every branch's exact behavior was traced against unmodified
`engine.py` via throwaway scripts first, including the exact computed
breakeven+cost price (`_compute_be_cost_pts`'s real default: 0.35).

## Tests first (TDD)

- `tests/core/test_tp_safety_net_characterization.py`:
  - BE Runner strategy -> immediate no-op (broker already manages the exit).
  - Already protected (`sl_moved_to_be` true) -> no-op.
  - EA-managed and the EA instance reports healthy -> no-op (the EA owns
    protection for this trade).
  - EA-managed but no EA instance (or unhealthy) -> falls through and
    protects normally, same as a non-EA trade.
  - Breakeven-trigger TP resolution: GD VIP Runner / Scalp Runner use TP2;
    every other strategy uses TP1.
  - No value at the resolved trigger TP field -> no-op.
  - Trade younger than 15 seconds -> no-op (fill may not be settled yet).
  - No M1 candles since open -> no-op.
  - Candle extreme hasn't reached the trigger TP -> no-op.
  - Reached, broker-side move succeeds -> `stop_loss`/`sl_moved_to_be`
    updated in the DB to the computed breakeven+cost price, an alert sent.
  - Reached, but price has already retraced past the breakeven+cost level
    ("window closed") -> no `modify_order` call, no DB write, a
    window-closed alert sent (once, respecting the cooldown).
  - Reached, `modify_order` raises -> no DB write, trade not marked
    protected.
  - Reached, `modify_order` returns `{"success": False}` (a broker
    rejection, not an exception) -> no DB write, a failure alert sent.
  - No `mt5_ticket` -> the broker call is skipped entirely, but the DB is
    still updated (the trade record is protected even with no live order to
    sync against).
  - `_tp_safety_net_sweep`: iterates every open trade, a per-trade exception
    is caught and doesn't stop the remaining trades from being checked.

## What to do

1. Write the test file using a fake bridge (`get_candles_range`/
   `modify_order`/`get_tick`), calling the methods via
   `SimulationEngine.__new__(SimulationEngine)` with
   `_tp_safety_net_last_alert = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

15 tests written in `tests/core/test_tp_safety_net_characterization.py`,
all green on the first run against unmodified `engine.py` -- every branch
pre-traced via throwaway scripts first, given the number of interacting
gates and the need for an exact expected breakeven+cost price
(`_compute_be_cost_pts`'s real default of 0.35 on top of entry, confirmed
via direct trace rather than hand-computed). No `engine.py` bugs found.

Confirmed the "protect the DB record even with no live order" behavior:
when `mt5_ticket` is falsy, `bridge.modify_order` is skipped entirely but
`stop_loss`/`sl_moved_to_be` are still written unconditionally -- the same
pattern already seen in several trade-handler packs, here applied to a
risk-management safety net rather than a strategy handler.
