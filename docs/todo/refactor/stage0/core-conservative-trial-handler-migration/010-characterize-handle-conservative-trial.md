# 010 — Characterize _handle_conservative_trial

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs (most recently
`core-scalp-runner-handler-migration`).

## Tests first (TDD)

- `tests/core/test_handle_conservative_trial_characterization.py`:
  - No TP cleared -> no-op.
  - TP1 cleared alone (5% close, no auto-close): doesn't return -- falls through to
    check TP2 (not cleared), call ends normally.
  - TP1 rejected by bridge: no DB write, cascades to check TP2 anyway (return value of
    `_partial` is `False` on rejection, same as a non-auto-closing success).
  - TP1 and TP2 both crossed in one tick (price gapped past both): TP1 closes 5%,
    cascades into TP2 in the same call -- TP2 closes 30% and moves SL to breakeven,
    then returns.
  - TP2 alone (TP1 already triggered from a prior call): 30% close + SL to
    breakeven, unconditional return regardless of whether the 30% close itself
    reported `auto_closed`.
  - TP2 with `sl_moved_to_be` already set: skips the SL move, still returns.
  - TP3 cleared alone (TP1/TP2 already triggered): 20% close, falls through to
    check TP4 (not cleared), call ends normally.
  - TP4 cleared: 40% close, SL steps to the TP2 price level (only if that's actually
    further from entry than the current SL), unconditional return.
  - TP4 SL-step guard: TP2 level is not beyond current SL -> no `modify_order` call,
    still returns.
  - TP5 cleared alone: 5% close, falls through to check TP6 (not cleared), call ends
    normally.
  - TP6 cleared: closes ALL remaining lots (not a fixed percentage), sends the tp6
    Telegram alert; if that empties the position, schedules `_close_full_after_tps`.
  - TP6 with zero remaining lots: no bridge call, no-op.
  - No `mt5_ticket`: DB still updates, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_conservative_trial` via
   `SimulationEngine.__new__(SimulationEngine)` with `_tp_cache = {}`,
   `_tp_wait_log_ts = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

13 tests written in `tests/core/test_handle_conservative_trial_characterization.py`.
No `engine.py` bugs found; two real, non-obvious characterization discoveries:

1. **Recurring `partial_close_trade` TP1 BE-move** (same finding as packs 22/23):
   fires here too on the TP1 branch (5% insurance close), moving `stop_loss` to
   breakeven at the DB level a full tier earlier than the handler's own docstring
   implies (which says SL only moves at TP2).

2. **New finding, specific to this handler's multi-TP-per-call design**: TP2's
   own SL-move guard (`current_sl`, `trade.get("sl_moved_to_be")`) reads from the
   `trade` dict captured once at function entry -- it is never re-fetched after
   TP1's `_partial` call mutates the DB via `partial_close_trade`. So when TP1 and
   TP2 are both crossed in a single tick/call (price gapped past both levels),
   TP2 still believes SL needs moving (using stale pre-TP1 values) and re-issues
   `bridge.modify_order` plus a second, duplicate "SL moved" Telegram alert --
   even though the DB-level SL was already correctly at breakeven from TP1's own
   side effect. The end DB state is still correct (same breakeven value written
   twice), so this is a harmless-but-real quirk: an extra broker sync call and a
   duplicate alert on the cascade path. Preserved verbatim, not fixed -- same
   precedent as the pack 19 "no logic changes during extraction" rule. The same
   stale-`trade`-dict pattern applies to TP4's SL-step-to-TP2-level logic
   (`trade.get("stop_loss")`), but no test exercises a cascade through TP1-TP4 in
   one call, so it wasn't separately characterized here.

Also confirmed: TP1/TP3/TP5 check `_partial`'s return value and only `return`
early on a true `auto_closed` outcome (letting a rejected or non-terminal close
cascade into the next TP check); TP2/TP4 always `return` once their TP level is
reached, regardless of whether `_partial` succeeded. TP6 closes ALL remaining
lots directly (not a fixed percentage) and is the only tier with a zero-remaining
guard.
