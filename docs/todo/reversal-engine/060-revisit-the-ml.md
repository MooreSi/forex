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


---

# Two things about the LABEL, found 2026-09-10

Both concern `_realised_r`, which is what the model regresses on:

```python
risk = float(row.get("sl_dist") or 0.0) * _DOLLARS_PER_POINT   # 0.1 lot -> $10/pt
net  = row.get("net_pnl_dollars")
return net / risk
```

## 1. The label is only correct while Fixed Lot Size is 0.10

`_DOLLARS_PER_POINT` is `_VIRTUAL_LOT * 100` with `_VIRTUAL_LOT = 0.1`, and its
comment says plainly it is "dollars per point for a **virtual** signal".

The numerator is not virtual. For an executed signal, `net_pnl_dollars` is the
real money the broker paid, at whatever lot actually traded. The two agree
today **only because Trading > Global Parameters has Fixed Lot Size set to
0.10**, which is the same $10 a point.

Change that dial to 0.02, or let risk-based sizing take over, and every
executed row's label is scaled wrong while every virtual row's stays right —
silently, with no error and nothing on screen. A UI setting would be
invalidating the training labels.

Nothing is changed here: dividing by the row's own realised risk is the fix,
but that needs a per-row lot size the table does not currently carry, and it
would change every historical label.

## 2. Executed and non-executed rows are labelled from different worlds

`get_ml_training_data()` selects every closed signal with features and does
**not** filter on `live_exec_status`. So the model trains on real broker
outcomes and the engine's own paper outcomes together, undistinguished.

That is defensible and probably right — training only on signals that passed
every gate is a textbook censored sample, and the model could never learn what
the gates correctly refused. But the two populations are not managed the same
way, and 2026-09-09's data shows it:

| | average loss |
|---|---|
| blocked signals, tracked on paper | **-$88.22** |
| real losses on the account that day | about **-$50** |

Same dollars-per-point, so that gap is not an artefact of the constant above.
The likely cause is management: a real trade is run by the EA template, with a
TP ladder, partial closes and a trail, while a virtual one runs to its stop.
**Paper losers are bigger than real losers**, so `y` carries a systematically
heavier left tail for the rows that were never executed.

Consequences worth holding:

* the model may be learning to avoid a loss shape that the EA's own management
  would have softened;
* any measurement comparing blocked against executed P&L — including the gate
  effectiveness table in
  [080](080-no-trend-gate-on-the-telegram-path.md) — **overstates what the
  blocked trades would really have lost.**

The honest fix is to label the two populations from the same management model,
or to carry the execution status as a feature so the model can tell them apart.
Neither is done here; this file is deliberately last.
