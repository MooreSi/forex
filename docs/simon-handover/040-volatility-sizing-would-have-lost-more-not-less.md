# 040 — Volatility sizing would have lost MORE, not less

**Status:** open, **for your decision**. Nothing on the order path has been
changed. The switch stays where it was: on the card, off, connected to
nothing.
**Money:** yes, directly — this is position sizing on every trade, every
engine.
**Found:** 2026-09-17, measuring before wiring rather than after.

## What you asked

To connect "Scale size by volatility and drawdown", and whether it would
improve entries and profitability.

## The first half of the answer is structural

**It cannot improve entries.** Sizing decides how big a trade is, never
whether to take it. Turn it on and the engine takes the same signals, at the
same prices, at the same times, in the same direction. Not one entry changes.
If entries are the problem — and on this book they are — sizing is the wrong
control entirely.

## The second half I measured, and the answer is no

5,116 closed Reversal Engine signals, each with the H1 ATR recorded at signal
time. Group them by how volatile the market was:

| ATR band | where that sits | trades | avg P&L |
|---|---|---|---|
| 3.13 – 5.34 | quietest 10% | 512 | **-$4.89** |
| 5.34 – 6.10 | | 512 | **-$6.53** |
| 7.12 – 7.74 | middle | 512 | **-$8.26** |
| 10.21 – 12.80 | | 511 | -$3.37 |
| 12.80 – 29.98 | most violent 10% | 511 | **-$2.25** |

The whole premise of volatility targeting is that violent markets are where
you get hurt, so you trade smaller there. **On this book it is the other way
round.** The violent decile is the *least* bad, at -$2.25 a trade. The quiet
and middle deciles are the worst, at -$6.53 and -$8.26.

So the policy would size *down* into the trades that lose least and size *up*
into the trades that lose most. Replaying every one of those 5,116 trades with
the scalar applied:

| | total P&L |
|---|---|
| as actually traded | -$22,318 |
| with volatility targeting | **-$23,431** |
| control: the same total exposure, spread flat | -$22,428 |

**-$1,113 worse**, and -$1,002 worse than simply trading that same total size
on every trade with no cleverness at all. That control matters: it rules out
"it only looks worse because it traded more". It traded the same amount. It
put it in the wrong places.

## The drawdown half is worse than useless here

The drawdown scalar tapers size from 5% below peak equity down to a floor of
a quarter at 20% below. The engine's own balance log:

* peak equity ever reached: **$511.53**, early on
* current: **-$22,299**
* entries sitting more than 20% below that peak: **9,748 of 9,824 — 99.2%**

The curve went underwater near the start and never came back. The peak is an
all-time high that will not be revisited for a very long time, so the scalar
is not a dial that responds to conditions. **It is pinned at its 0.25 floor
permanently.**

That would cut every lot to a quarter, forever. It would indeed reduce losses
— by about three quarters, because the book loses money and trading less of it
loses less. But that is not a risk policy doing its job. It is a 75% size
reduction with a formula wrapped around it, and if that is what you want, you
should set it deliberately in Max lot size where you can see it, not arrive at
it as the side effect of a scalar.

## What I have and have not done

**Not done: the wiring.** It touches `suggest_lot_size`, which has 20-odd call
sites across seven modules and serves every engine and both manual order
paths. It is position sizing on a live account, so it needs your sign-off and
a demo session regardless of the numbers — and the numbers say don't.

**Done: fixed a real bug in it while it is still inert.** `sizing_policy.apply`
had no upper lot ceiling of its own, and its volatility scalar has an upside of
1.5x. With 98% of your trades sized at exactly the 0.10 Max lot size cap, a
quiet market would have returned **0.15 lots — half again over a cap you set**.
Nothing caught it because nothing calls the function yet. Fixed, with the
account's Max lot size now carried through, and pinned by
`tests/risk/test_sizing_policy_respects_the_lot_ceiling.py`.

## What I would do instead

The book loses $4.36 a trade across 5,116 trades. No sizing rule fixes that;
it only changes how fast. The controls that decide *which* trades get taken
are the ones on the same card and they have measured evidence behind them:

* **"Require confirmation, not just arrival"** — fills inside five minutes are
  453 trades at -$1,950.
* **"Level types to refuse"** — `round_5` is 210 trades at -$1,323 and the
  scorer rates it highest of all.

Both change entries. Sizing cannot.

## What I need from you

1. **Leave the sizing switch off?** That is my recommendation, and it stays off
   unless you say otherwise.
2. **If you want it on anyway**, say so and it goes on the demo-session list —
   it is a money-path change and I will not connect it without one.
3. **Do you want the permanent quarter-size effect deliberately?** If the real
   intent is "trade smaller while this book is losing", Max lot size is the
   honest place to do it, and it is one number you can see and undo.
