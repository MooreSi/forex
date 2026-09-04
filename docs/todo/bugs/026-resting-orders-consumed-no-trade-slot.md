# 026 — A cap of 3 opened more than 3: resting orders consumed no slot

**Status:** fixed 2026-09-04, test-first. NOT VERIFIED AGAINST A BROKER —
this gates real order placement and wants a demo session.
**Found:** live, 2026-09-04, reported by the owner: "the max open trades in
the risk settings is set to 3, why has it opened more trades?"
**Touches money:** yes — it decides whether an order is placed at all.
**Severity:** the cap could be exceeded without limit by the pending-order
paths; the only always-on protection the account has was bypassable.

## Root cause

Two separate things, one of them a real hole.

**(a) Not a bug, but worth knowing.** The cap counts ROWS in
`vantage_simulated_trades`. One EA Template trade is one row and `anchors` +
`pendings` broker positions, so 3 rows is legitimately 6+ positions in the MT5
terminal. Counted in the terminal, "more than 3" is expected.

**(b) The hole.** A resting order consumed no slot at either end:

* not when placed — `reversal_engine_repo.claim_vantage_signal_activation`
  had no cap in its WHERE at all (documented as a deliberate open question
  since 2026-08-30: "whether a resting order should consume a trade slot is a
  money decision for the owner"), and the Limit Runner path creates its signal
  already `pending` beside a `working` order, which nothing counted;
* not when it filled — `broker_repo.apply_pending_fill` INSERTs an `open` row
  directly, and the only market-order backstop lives in `open_trade`, which
  that path never calls.

So N resting orders became N open trades over any cap, with the cap never
consulted.

## The owner's decision

> "whether it is a resting order or a market order the EA should manage the
> max number of allowable trades as set within the gui"

A slot is held from the moment an order exists until the position it becomes
is closed.

## What changed

One definition, `signal_state_repo._SLOTS_IN_USE_SQL`: open positions +
orders resting at the broker + opens in flight. Used by the canonical claim,
the Reversal Engine's claim (which now has a cap), `open_trade`'s backstop,
and the three pre-checks. `count_slots_not_yet_open()` is the half for callers
that already hold an open-trades list, so nobody re-derives the rule.

Two things the tests forced out:

* **No double-count.** The Reversal Engine leaves its signal `activating`
  while its own order is already `working` (it reaches `active` only at fill,
  inside `apply_pending_fill`), so counting both charged one order two slots.
  A `NOT EXISTS` keeps the terms exclusive.
* **A signal must not block itself.** The claim runs first, then `open_trade`
  for the same signal — counting in-flight claims without excluding the caller
  refused EVERY trade at a cap of 1. Caught by
  `test_signal_resolution_characterization` (7 failures), fixed with
  `exclude_signal_id`, which excludes only the not-yet-open half: an open row
  on the same signal is a position that exists.

## Verification

`tests/trading/test_resting_orders_consume_a_slot.py` — 24 cases, red first.
`tests/core/test_manual_order_exemptions.py` had its mock target moved from
`trade_repo.count_open_trades` to `signal_state_repo.count_trade_slots_used`
(same gate, same assertions, same negative control — only the faked function's
name changed), approved by the owner and verified it can still fail.

## Sign-off needed

A demo session before this is trusted: it makes the app REFUSE orders it
previously placed. The failure mode to watch for is over-refusal — a leaked
`activating` claim or a stale `working` row now holds a slot that nothing
frees (`release_stranded_activations` covers the first).
