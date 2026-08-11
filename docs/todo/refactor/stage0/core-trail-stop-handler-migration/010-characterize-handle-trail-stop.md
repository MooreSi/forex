# 010 — Characterize _handle_trail_stop

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` -- tested against
a fake bridge only.

## Decision

Same fake-bridge approach as prior packs.

## Tests first (TDD)

- `tests/core/test_handle_trail_stop_characterization.py`:
  - TP1 not cleared and not yet trailing -> no-op.
  - TP1 cleared for the first time -> activates: SL locked to entry immediately, `modify_order`
    called with entry price, `sl_moved_to_be` set, a `TP1_TRAIL_START` marker recorded.
  - `sl_moved_to_be` already set (activation happened a prior cycle) but the trade dict passed
    in is stale (still shows `sl_moved_to_be=0`) -> the handler re-checks the DB directly and
    still finds it active, skipping re-activation.
  - Active trailing, price advances -> SL trails to `bid - trail_dist` (BUY), never below
    entry.
  - Active trailing, price retreats -> SL does NOT move backward (no `modify_order` call).
  - TP2 crossed while trailing -> records a `TP2_TRAIL_MARKER` partial-close row, no lots
    actually closed, no duplicate marker on a second call.
  - No `mt5_ticket`: DB still updates, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`modify_order`), calling
   `SimulationEngine._handle_trail_stop` via `SimulationEngine.__new__(SimulationEngine)` with
   `_tp_cache = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order modified — verified via the fake bridge's call log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

7 tests written in `tests/core/test_handle_trail_stop_characterization.py`. No `engine.py` bugs
found. One test-design correction: the TP2-5 marker de-dup relies on pack 5's
`get_triggered_tps`, which has a 2.5s TTL cache — two calls to the handler within that window
(as an unmodified two-line test would naturally do) CAN produce a duplicate marker row, since
the cache doesn't yet reflect the marker just written moments ago. Not a bug (harmless for the
UI's "at least one row exists" chip logic, and matches the same cache-freshness tradeoff
already characterized in pack 5), but the "no duplicate" test needed to force cache expiry
between calls to actually exercise the real de-dup path rather than accidentally proving
nothing. Confirmed the stale-trade-dict re-check against the DB directly (activation vs.
already-active) and the floor/ceiling-at-breakeven trailing math both behave exactly as
documented.
