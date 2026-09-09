# 090 — `level_score` switches off the bias filter, and it does not predict anything

**Status:** **BUILT 2026-09-09 as option A, off by default, NOT DEMOED.**
**-$219.43 on 2026-09-08 alone, across six trades.**
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


---

## Built 2026-09-09 — option A, behind the same switch

When `htf_bias_gate_enabled` is ON the shared rule decides and `level_score`
grants no bypass. When it is OFF the original `level_score < 0.75` behaviour
stands untouched, so the default install is byte-identical to before.

Written as `_bias_block or (<the original condition>)` rather than by deleting
the old test: with the switch off the old behaviour must survive exactly, and
leaving it visible makes that obvious to the next reader.

### Still open, and worth a decision

**Neutral bias loses too** — -$1,234 over 184 trades, as much as counter-bias.
The gate does not block it, because "no clear trend" is a different claim from
"the trend is against you". Blocking both would leave only the 369 with-bias
trades, which are collectively **+$101.41** — the difference between a losing
system and a marginally profitable one on the same history.

That is a much larger change and it is the owner's call. Measure it properly
first: some of "neutral" may be the bias being unreadable rather than genuinely
flat, and those are not the same thing either.
