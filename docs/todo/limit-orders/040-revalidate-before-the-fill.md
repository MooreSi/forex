# 040 — Re-judge a resting order before it fills, and withdraw it if the setup has gone

**Status:** **BUILT 2026-09-10**, owner-signed-off, tests-first. `python -m tools.checks all` green. **NOT DEMOED** — no broker has seen any of it.
**Depends on:** none (independent of 010-030, but the value rises once template limits rest here too)
**Real-money surface:** yes — it cancels live broker orders, and re-places them. Owner sign-off before implementation; demo before trusted.
**Leverage:** the sweep, the toggle and the cancel call all exist; only the gate set and the outcome change.

## Problem

A resting order can sit for up to `_DEFAULT_EXPIRE_MINUTES` (60) before it fills, and MT5 fills it
directly with no round trip back to Python. The market it fills into is not the market it was created
in.

[reversal-engine/100](../reversal-engine/100-revalidating-every-waiting-order.md) fixed this for the
*queued Telegram signal*, which now re-asks the trading schedule, the news blackout and
`governor.fill_too_soon` at activation, on top of the pre-trade filters and M5 momentum it already
asked (`pending_activation.py:432-525`). It said so in its own "Still open":

> **Only the bias is re-checked on a resting order.** Schedule and news are not.

`revalidate_resting_orders` (`resting_revalidation.py:35`) asks `governor.htf_bias_blocks` and
nothing else, only when `htf_bias_gate_enabled` is on, and only logs the outcome. So the identical
setup is judged one way if it waits in Python and another way if it waits at the broker.

## Decision

Widen the sweep to full parity with the queued path — schedule, news blackout, fill delay, pre-trade
filters, M5 momentum, plus the bias it already asks — using **the same functions, not copies**. The
whole argument of reversal-engine/100 is that a second implementation of "are we in a blackout" is
how two routes come to disagree.

**Proximity-triggered** (owner, 2026-09-10): the cheap bias check keeps running on every 60s sweep;
the full gate set runs only once price is within **10 points** of the resting price. Roughly a minute
or two of gold movement, so a withdrawal lands before the fill without re-running every gate for an
order 50 points away, and without discarding an order an hour early over a condition that would have
cleared by fill time.

**Withdraw and re-arm** (owner, 2026-09-10): a failed gate cancels the broker order but does not kill
the setup. The row stays alive until its **original** TTL, and is re-placed if every gate passes
again before then. A news window or a schedule edge is temporary; the setup it interrupts is not.

The re-arm is the part with teeth. Three things it must not do:

1. **Extend the life of the order.** The re-placed order expires at the original expiry timestamp,
   not 60 minutes from re-placement. Otherwise a flapping gate makes an order immortal.
2. **Re-place at a drifted price.** The resting price, SL and TPs are re-used exactly. If the levels
   would have to move for the order to be valid, that is not a re-arm — leave it withdrawn.
3. **Double up.** A withdrawn row must be unambiguously distinguishable from a working one, or the
   sweep re-places an order that is already on the book. `vantage_pending_orders.status` is
   `'working'` today and `fetch_working_pending_orders` filters on it; add one new status rather than
   overloading `'cancelled'`, which means "gone for good".

## Tests first (TDD)

**Written 2026-09-10, red before any fix.** Two files, 31 tests, **15 red**.

[`tests/core/test_resting_revalidation_gates.py`](../../../tests/core/test_resting_revalidation_gates.py)
— 19 tests, 8 red, 11 green.

Each gate is patched **at the module where it is defined**, so an implementation that copies one, or
binds it with `from x import f` at import time, fails here. `resting_revalidation.py` already calls
`_gov.htf_bias_blocks` through its module for exactly that reason.

Red: the schedule, the news blackout, the fill delay, the pre-trade filters and a contrary M5 candle
each withdraw the order; proximity acts at 9 points; the trend gate's toggle no longer governs the
other checks; and the signature takes a `tick` and `dpm_candles` at all.

Green, and already true today: an unreadable bias withdraws nothing, an order with no broker ticket
is left alone, a throwing gate does not take the sweep down, a turned bias still withdraws, the bias
is asked at any distance, and nothing is withdrawn when every gate passes.

`revalidate_resting_orders` does not take a tick or candles yet, so the test file passes only the
kwargs the current signature accepts. Without that, all 19 failed with the same `TypeError` and the
run said nothing about which behaviour was missing. `test_the_signature_takes_the_market_it_is_
judging_against` is what stops the shim standing in for a parameter that never gets added.

`TestItNeverCloses` is the named test `resting_revalidation.py`'s docstring promises, carried
forward: it reads the module's own source and fails if `close_trade`, `record_close`,
`_make_close_trade_ctx` or `partial_close_trade` appears outside the docstring. It has its own
negative control, because a source search that matches nothing looks identical to one that passes.

[`tests/core/test_resting_revalidation_rearm.py`](../../../tests/core/test_resting_revalidation_rearm.py)
— 12 tests, 7 red, 5 green. **Real database, not a fake repo**: the whole question is what state the
row is left in, and a fake would answer it with whatever the test imagined.

Written against the three ways re-arm goes wrong, not the happy path:

* **the immortal order** — seeded 45 minutes into a 60-minute life, a correct re-arm asks for ~15
  minutes, not another 60. `vantage_pending_orders` has **no expiry column**, so the original clock
  has to be derived from `created_at` — exactly the detail a test written after the code would have
  quietly ratified.
* **the drifted order** — re-placed at the stored price, stop, targets, lot and strategy, never at
  "the current near edge".
* **the doubled order** — a working row is never re-placed, a cancelled one never comes back, and
  withdraw → re-arm → withdraw ends with exactly 2 cancels, 1 place and one live order at every
  point.

Plus: a withdrawn row must not read `cancelled` (that status is final and `apply_pending_cancelled`
cancels the signal with it, which would make re-arm impossible), the signal row stays `pending`, a
broker refusal leaves the row withdrawn rather than stranding it as working, and an order past its
original TTL is marked something that is neither `withdrawn` nor `working` so it is not reconsidered
forever.

**Honest note on the green ones there:** the "never does X" tests pass today because nothing is ever
re-placed at all. They are guards for after the feature exists, and are the ones to break
deliberately once it does.

**Names these tests pin** (change them here and in the tests together): the tunable
`resting_revalidation_enabled`, the row status `withdrawn`, and `tick` / `dpm_candles` on the sweep's
signature.

## What to do

1. ~~Write the tests above; run them; confirm they fail for the right reason.~~ Done 2026-09-10.
2. Add the new `status` value and its repo reads/writes. Check the migration conventions before
   touching the table.
3. Widen `revalidate_resting_orders`: keep the bias check where it is, add the proximity test, and
   behind it call the same gate functions `pending_activation.py` calls. Import them; do not
   re-implement.
4. Add the re-arm pass. It belongs in the same sweep — one function that owns the whole
   working/withdrawn lifecycle is easier to reason about than two that each own half.
5. Keep the whole thing non-raising. It runs on a loop and a bad sweep must not take the cycle down;
   the existing function already promises this in its docstring.
6. Wire the alerts from [050](050-announce-a-discarded-limit-order.md).
7. Record what was learned in the relevant `docs/system/domains/` file.

## Where

- `backend/src/services/trading/resting_revalidation.py` — the sweep; likely outgrows 85 lines, check the LOC ratchet
- `backend/src/services/positions/monitor_cycle.py:188-202` — the 60s call site
- `backend/src/services/signals/pending_activation.py:432-525` — the gate set to reuse
- `backend/src/services/broker/repo.py:22-37` — `fetch_working_pending_orders` and friends

## Acceptance

- A resting order whose schedule, news, momentum, R:R or bias has turned against it is withdrawn
  before price reaches it, with the reason recorded.
- The same order is re-placed, unchanged and on its original clock, if the condition clears in time.
- No path here can reach a close. `close_trade`, `record_close`, `_make_close_trade_ctx` and
  `partial_close_trade` are untouched.
- **The killer test:** a resting BUY, a news blackout opening while price is 8 points away, the order
  withdrawn, the blackout ending 10 minutes later, the order re-placed at the identical price with
  the original expiry — and exactly one broker order alive at every point in that sequence.

## Notes

**Its own tunable, default on** (owner, 2026-09-10). Today the sweep is gated on
`htf_bias_gate_enabled`, the trend gate's own switch; reusing it would mean turning the trend gate off
silently turns off the news re-check too. `htf_bias_gate_enabled` keeps governing only the bias half.
Add the new setting via the `/add-tunable` skill — it is a behaviour constant that must be
user-editable, which is exactly what that skill exists for.

Out of scope, and still true from reversal-engine/100: orders placed by hand on the terminal are
invisible to this sweep, because it reads `vantage_pending_orders`.
