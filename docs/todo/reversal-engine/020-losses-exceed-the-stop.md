# 020 — Losses average -1.161R against a stop that is 1.0R by definition

**Status:** open, **blocked on data until roughly 2026-09-22.**
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
