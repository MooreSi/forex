# 010 — Characterize _handle_no_sl_scale

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs (most recently
`core-conservative-trial-handler-migration`).

## Tests first (TDD)

- `tests/core/test_handle_no_sl_scale_characterization.py`:
  - No TP columns set on the trade at all -> no-op (early return before any TP check).
  - TP1 cleared, it's the only defined TP (`last_tp_num == 1`) -> closes all remaining
    lots, returns.
  - TP1 cleared, more TPs exist -> 20% partial close; falls through (no early return)
    to check TP2, which isn't cleared, so the call ends normally.
  - TP1's level is behind the fill price (e.g. instant entry inside signal zone) and
    the market is at/better than breakeven -> partial-closes 20% at the *market*
    price, not the (already-passed) TP1 level.
  - TP1's level is behind the fill price and the market has NOT recovered to
    breakeven -> marks TP1 skipped, no partial close, no SL move.
  - TP2 cleared, `last_tp_num == 2` -> closes all remaining, returns.
  - TP2 cleared, more TPs exist -> marks TP2 skipped only (no partial close, no SL
    move) -- TP2 never partial-closes or moves SL by design.
  - TP3 cleared, `last_tp_num == 3` -> closes all remaining, returns.
  - TP3 cleared, more TPs exist -> 20% partial close + SL moves to the TP1 level (or
    to entry price if TP1 itself is behind entry).
  - TP1+TP2+TP3 all crossed within one tick (price gapped past all three): TP1
    closes 20%, TP2 is marked skipped, TP3 closes 20% and moves SL -- but TP3's SL
    move compares against the `current_sl` local captured once at function entry,
    NOT the value `partial_close_trade`'s own TP1 breakeven side effect just wrote
    to the DB a few lines earlier in the same call. A genuine quirk to characterize
    and preserve, not fix.
  - TP4 cleared, not the last tier -> SL steps to the TP2 level (`tp{n-2}`), TP4
    marked skipped, no partial close.
  - TP4's SL-step target isn't actually beyond the (stale) `current_sl` -> no
    `modify_order` call, TP4 still marked skipped.
  - A TP within the TP4-7 loop that IS the last defined tier -> closes all
    remaining, returns (same as the TP1/TP2/TP3 last-tier branches).
  - TP8 cleared as the final, dedicated branch (only reached when
    `last_tp_num == MAX_TP`, since the TP4-7 loop's range never includes index 8)
    -> closes all remaining lots.
  - No `mt5_ticket`: DB still updates (partial close still recorded), bridge never
    touched.

## What to do

1. Write the test file using a fake bridge (`partial_close`/`modify_order`), calling
   `SimulationEngine._handle_no_sl_scale` via
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

15 tests written in `tests/core/test_handle_no_sl_scale_characterization.py`,
all green against unmodified `engine.py`. No `engine.py` bugs found; two real,
non-obvious characterization discoveries:

1. **Recurring `partial_close_trade` TP1 BE-move** (same finding as packs
   22/23/24): fires on this handler's TP1 branch too, moving `stop_loss` to
   breakeven at the DB level even though this handler's own TP1 code never
   touches SL (TP1 here is purely a 20% partial close).

2. **New finding, specific to this handler's `current_sl` local variable**:
   unlike `_handle_conservative_trial`'s stale-`trade`-dict quirk (a dict
   field), here it's a plain `float` captured once at function entry. When
   TP1+TP2+TP3 all cross in a single tick, TP3's `_move_sl` call compares its
   target against that same stale pre-call `current_sl` (the original
   emergency SL), not the breakeven value `partial_close_trade` already wrote
   to the DB from TP1's own side effect a few lines earlier in the same call.
   Verified via a direct trace (not just test output): with `current_sl`
   captured as 2380.0 and TP1's side effect already having written 2400.0 to
   the DB, TP3's move to 2405.0 (TP1's price level) compares `2405.0 > 2380.0`
   (stale) rather than `2405.0 > 2400.0` (live) — same qualitative outcome in
   this specific case since both comparisons are True, but the DB's actual
   pre-move value was never consulted, so a configuration where the "live"
   comparison would differ from the "stale" one is a live, reachable
   inconsistency in the original code. Preserved verbatim, not fixed, same
   precedent as every prior pack's "no logic changes during extraction" rule.

Also confirmed: TP1/TP2/TP3 each have an "is this the last defined tier"
branch that closes everything and returns; TP4-7 share one loop that steps SL
to `tp{n-2}` and marks the tier skipped unless it's the last tier (then
closes all); TP8 is a dedicated final branch only reachable when
`last_tp_num == MAX_TP` (8), since the TP4-7 loop's `range(4, min(last_tp_num
+ 1, MAX_TP))` structurally excludes index 8. TP1 has a unique "behind the
fill price" fallback (when TP1's own level is already on the wrong side of
entry) that either partial-closes at the live market price once price
recovers to breakeven, or marks TP1 skipped and defers to TP3+ if price
hasn't recovered.
