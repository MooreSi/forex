# 020 — Losses average -1.161R against a stop that is 1.0R by definition

**Status:** open, **blocked on data until roughly 2026-10-01** — re-estimated
2026-09-10 from the real collection rate, and the planned analysis has a
measurement bias that has to be handled first. See the end.
**Money:** yes — it is where the stop sits.

## The measurement

Executed and closed, 302 losses: mean **-6.28 points** against a mean
`sl_dist` of **5.75**. That is **-1.161R** where the stop defines 1.0R, so
roughly **0.53 points of leakage per loss — about 160 points over the sample.**
`ml_engine.py` already recorded a worst case of -5.75R.

## Why it matters more than anything else on the list

Hold losses to exactly 1.0R and **nothing else changes**: break-even falls from
64.4% to 60.9%, against an actual win rate of 59.4%.

## Why it is blocked

The cause is not yet known — slippage, gapping, or the stop not being where the
row believes it is. Telling them apart needs `mae_pts`, which the live path
never recorded until 2026-09-08 (see data-inspect/003 part 3). **Of 745
executed signals only 52 carry an excursion figure and none in September.**

`_record_live_excursion` now collects it. Give it a fortnight of live running,
then compare `mae_pts` against `sl_dist` per trade: a stop honoured exactly
gives `mae ≈ sl_dist`, slippage gives a small consistent excess, a gap gives a
large occasional one, and a misplaced stop gives an excess that correlates with
the strategy rather than with volatility.


---

# Measured collection rate, and a bias in the planned analysis (2026-09-10)

## The data is arriving, more slowly than the estimate assumed

`_record_live_excursion` has been running since 2026-09-08. Counting only the
population this item needs — **live-executed** signals carrying an excursion:

| | count |
|---|---|
| executed signals, all time | 765 |
| of those, with an excursion | 68 |
| of those, losses | 26 |
| collected since 2026-09-08 | 18 (9 win / 9 loss) |

That is **9 a day executed-with-excursion, 4.5 of them losses.** Reaching 100
losses takes about **20 more days**, not the fortnight this file estimated —
so early October rather than 2026-09-22. The estimate assumed every executed
signal would carry one; most do not, because a signal has to be live-executed
AND still open across at least one sampling tick.

## The bias — read this before running the comparison

This file's plan is:

> compare `mae_pts` against `sl_dist` per trade: a stop honoured exactly gives
> `mae ≈ sl_dist`, slippage gives a small consistent excess, a gap gives a
> large occasional one

**`mae_pts` cannot support that comparison as written.** It is sampled once per
five-second outcome loop, and `_reconcile_live_signal` says so itself: *"this is
the ONLY moment the live path sees a running price -- so it is where the
excursion has to be taken."* A move that reaches the stop and closes the
position between two samples is never recorded.

So the measurement is biased **downwards, specifically for fast moves** — which
are exactly the moves that hit stops. A correctly-honoured stop will frequently
read `mae < sl_dist`, and the comparison would conclude the stop was never
reached when it was.

The first 9 losses carrying both figures show precisely that shape, and they
are far too few to mean anything on their own:

| ratio `mae/sl_dist` | n |
|---|---|
| mean | 0.821 |
| median | 0.686 |

Five of the nine sit between 0.55 and 0.69 — the excursion never getting near a
7.00-point stop, on trades that nonetheless lost about $50.

**Do not read that as "losses close before the stop".** It is what a
5-second sampler does to a fast move. Before this analysis is worth running,
the excursion needs a final sample taken **at close** (from `close_price`,
which is already stored) so the watermark includes the move that ended the
trade. That is a small change to `_record_live_excursion`'s caller and it is
not made here, because it changes what the column means mid-collection and the
existing rows would need excluding from any comparison.

## One observation while looking, unrelated to the above

Every one of those 9 losses is between **-$45.30 and -$51.30**, whatever the
stop distance (4.00, 5.00 or 7.00 points). That is Fixed Lot Size 0.10 doing
what it does: 0.1 lots of gold is $10 a point, so the dollar loss tracks the
excursion and ignores `risk_per_trade_pct` entirely.

Worth knowing because **Risk per trade (%) reads 0.50** in Settings, which on a
$900 account is $4.50. The actual risk per trade is about **$50, roughly 5% of
the account**, because a fixed lot overrides risk-based sizing. That is the
configured behaviour, not a fault — but the two numbers on that screen say very
different things about how much is at stake.
