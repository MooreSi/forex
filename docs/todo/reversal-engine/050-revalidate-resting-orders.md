# 050 — Re-check a resting order before it fills

**Status:** **BUILT 2026-09-09, NOT DEMOED.** Runs whenever the bias gate is
on — it shares that toggle, because it is that gate asked a second time.
**Money:** yes — it cancels orders that would otherwise fill.
**Raised by the owner, 2026-09-08:** *"if there are pending/resting trades
before they execute re-evaluate whether they are still valid to ensure they
should still be executed based on market conditions"*.

## Correct in principle, smaller than it looks

The measurement in 040 shows staleness costing little: over 60 minutes is
-$214 across 54 trades, against -$2,023 for the instant fills. So this is worth
doing and it is **not** where the money is.

## Part of it already exists

`reversal_engine_live_execute.py` already re-evaluates `ml_prob` at fill time
and falls back to the creation-time value if that fails — see the
`fill-time re-evaluation failed ... falling back to creation-time ml_prob`
warning. What does not exist is a re-check of whether the LEVEL is still valid.

## The constraint that matters

Use the same rule as 040. One definition of "is this level still valid",
called from both places.


---

## Built 2026-09-09 — it reuses the bias gate, not 040's rule

This file said it should share 040's rule. On reflection that was the wrong
pairing: 040 is about a fill arriving too FAST, and staleness is the opposite
direction. **The rule it actually shares is the bias gate's.**

**The argument, which needs no new evidence.** `governor.htf_bias_blocks` is
evaluated once, when the order is PLACED. A limit order can then rest for the
better part of an hour and fill into a bias that has since reversed — at which
point it is a counter-bias trade the gate would have refused had it been asked.
Re-checking is that same gate asked at the moment it matters.

**The direct evidence is thin, and is deliberately not what justifies it.**
Signals whose `htf_bias_at_fill` differs from `htf_bias` are **20 trades at
-$12.08 each**, against -$2.84 for the 737 where it held — the right direction,
four times worse, and far too small a sample to carry a money-path rule alone.
What carries it is the gate's own record: 201 counter-bias trades at
-$1,210.98.

## What it does

`trading/resting_revalidation.revalidate_resting_orders()` reads the working
pending orders and withdraws each one the current bias now refuses. Swept from
the Reversal Engine's outcome loop on its **own 60-second interval** — that
loop runs every 5s and a cancel sweep does not need to, the bias being an H1
read cached for a minute.

**It cancels; it never closes.** A resting order has no position, so the worst
it can do is withdraw an order that never filled. A test asserts by name that
`close_trade`, `record_close` and `position_close` appear nowhere in the module.

Fails open throughout: gate off, neutral or unreadable bias, unreadable rows,
a missing ticket, or one order the EA refuses — none of them stops the sweep or
withdraws anything it should not.

## Proof

16 tests, red first. Five mutants killed, and **two of the five needed work
rather than acceptance**:

* Deleting the module's own toggle check *looked* survivable, because
  `htf_bias_blocks` carries its own — the sweep cancels nothing either way. But
  without it the sweep still reads the pending orders every minute on every
  install with the feature off. The added test asserts the fetch never happens.
* The missing-ticket mutation reported as survived and had **not actually been
  applied** — the pattern missed a comment between the `if` and its `continue`.
  Re-run against the real source, it fails immediately. That is the
  `mutation-testing-wrong-target` trap, and a survivor is worth re-checking
  before it is believed.


---

## Moved out of the Reversal Engine, 2026-09-09 (night)

The sweep was invoked from `ReversalEngine._check_outcomes`. It sweeps
`fetch_working_pending_orders()` — **every** working order, including Limit
Runner orders placed from a Telegram signal, which have nothing to do with this
engine.

`_cycle_loop` runs `while self.is_running`, and the owner can stop the engine
from its panel. **Stopping it also stopped revalidating Telegram resting
orders**, with nothing on screen to say so. `_check_outcomes` also returns
early when there is no tick, skipping the sweep again.

Same shape as the trend gate missing `scan_auto_execute`
([080](080-no-trend-gate-on-the-telegram-path.md)): a protection that covers
every route, reachable only through one of them.

It now runs from the monitor cycle, alongside the other cross-cutting sweeps
(equity protect, basket harvest, orphan reconcile), with the same once-a-minute
throttle the orphan sweep uses. Placed **outside** the `if open_trades` block
deliberately: the case this feature exists for is a resting order with nothing
open yet, which is exactly when that block does not run.

The swept function is unchanged. Pinned by
`tests/trading/test_resting_sweep_is_not_tied_to_the_reversal_engine.py`; two
mutants — the sweep made unreachable, and the sweep nested back inside the
open-trades block — both die.
