# 090 — `level_score` switches off the bias filter, and it does not predict anything

**Status:** open. **-$219.43 on 2026-09-08 alone, across six trades.**
**Money:** yes.
**Found:** 2026-09-08, [data-inspect/004](../data-inspect/004-why-2026-09-08-lost-1270.md).

## The rule

`reversal_engine_live_execute.py`:

```python
if ((fresh_htf == "bullish" and direction == "SELL" and level_score < 0.75)
        or (fresh_htf == "bearish" and direction == "BUY" and level_score < 0.75)):
```

A counter-bias trade is blocked **only if `level_score` is below 0.75.** A
high-scoring level is trusted to trade against the higher timeframe.

## Why that is the wrong way round

`level_score` does not rank outcomes. Measured over all executed history in
[data-inspect/003](../data-inspect/003-why-the-reversal-engine-got-worse.md):

| level_score | n | win % | total |
|---|---|---|---|
| 0.6 | 232 | 56.9 | -$581 |
| 0.7 | 42 | 66.7 | -$7 |
| **0.9** | **400** | 60.5 | **-$1,378** |

**The highest-scoring band is the biggest loser.** So the bypass is granted by
a number that carries no information about whether the trade will work — and it
is granted precisely when the trade is counter-trend, which is when the
protection matters.

2026-09-08 executed six counter-bias signals. **All six scored >= 0.75. All six
lost, -$219.43.** With-bias trades the same day made +$96.53.

## Options

- **A. Make the bias a hard gate.** No bypass. Simplest, and today it would
  have saved $219.
- **B. Keep a bypass but gate it on something measured to work.** Nothing
  currently qualifies — `ml_prob` was anti-predictive before v9 and has 23
  trades since.
- **C. Raise the threshold.** Cosmetic: the 0.9 band is the worst, so a higher
  bar admits worse trades.

**A is the honest default until something is shown to rank outcomes.**

## Do not fix this in isolation

[080](080-no-trend-gate-on-the-telegram-path.md) is the same problem on the
larger route. One bias rule, applied on the shared path, covers both — two
implementations that can disagree is how this class of bug starts.
