# 060 — Revisit the ML gate, but only after 020-040

**Status:** open, deliberately last.

## Why last

The gate blocks when predicted R < 0, and `re_ml_meta.pkl` records `mean_r` of
**-0.083** at every retrain. The model is regressing R on a population whose
average R is negative, so **the better it gets, the more it blocks**. It is
currently the most honest component in the system: it has correctly learned
that the engine's own signals lose money.

Items 020, 030 and 040 change what it is learning from. Tuning it before they
land would be fitting to a population that is about to change.

## Two things to check when the time comes

**Does the score rank outcomes yet?** Before v9 it was *anti*-predictive on 741
executed trades — losers averaged `ml_prob` 0.1485, winners 0.1079. Under v9
the sign has flipped (losers 0.0409, winners 0.1101) but on 23 trades, which is
far too few. Re-measure on a real sample.

**`level_score` does not rank outcomes either**, and nothing has been done about
it:

| level_score | n | win % | total |
|---|---|---|---|
| 0.6 | 232 | 56.9 | -$581 |
| 0.7 | 42 | 66.7 | -$7 |
| 0.9 | 400 | 60.5 | **-$1,378** |

The highest-scored band is the biggest loser. Two of the engine's own
confidence measures fail to rank realised R. **Validate any ranking signal
against realised R before trusting it** — do not assume it works from its name.

## Also worth doing here

The five macro features v9 added are constant for ~96% of the training rows
(back-filled neutral before 2026-09-07). Re-check their importance once enough
rows carry real values, rather than assuming the bump helped.
