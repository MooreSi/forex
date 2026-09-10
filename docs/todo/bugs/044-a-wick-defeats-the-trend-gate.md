# 044 — A 3.53-point wick turns the trend gate off

**Status:** OPEN, **nothing changed** — the rule decides which trades are
taken, so it is the owner's call.
**Money:** yes. This is the gate that exists to stop the 2026-09-08 loss.
**Found:** 2026-09-10 12:55, live, while the account was losing on BUYs.

## What was happening

Gold fell **60.90 points** over fourteen H1 bars (4419.36 → 4358.46). The
account took **28 BUY closes for -$240.45** against 4 SELLs for +$182.54, and
the Reversal Engine's own executed trades read **bullish bias + BUY: 4 losses
to 1 win**.

`get_htf_bias` returned **`neutral`** throughout. `htf_bias_blocks` returns
None on neutral by design, so **every BUY passed the gate.**

## Why

`level_detector.get_htf_bias` splits the window in half and requires **both** a
lower high **and** a lower low:

```python
lh = h_second < h_first
ll = l_second < l_first
if lh and ll: bias = "bearish"
```

On the live 20-candle window:

| | first half | second half | |
|---|---|---|---|
| max high | 4431.23 | **4434.76** | +3.53 → `lh` is **False** |
| min low | 4389.79 | **4324.03** | −65.76 → `ll` is True |
| close | 4399.11 | 4357.27 | **−41.84** |

**A single wick 3.53 points — 0.080% — above a prior high is the whole
difference.** Price made a 66-point lower low and closed 42 points down, and
the indicator called it neutral.

## Every other reading of the same window says bearish

| rule | verdict |
|---|---|
| current: wick highs/lows, both conditions | **neutral** |
| closes instead of wicks | bearish |
| mean close, first half vs second (4407.48 → 4380.13) | bearish |
| 0.1% tolerance on the high comparison | bearish |
| either condition rather than both | bearish |

## Why it matters more than it looks

[080](../reversal-engine/080-no-trend-gate-on-the-telegram-path.md) measured
that the gate is worth having: 43 blocked signals at 74% win rate still lost
money, because losers were 5.5x winners. It also measured that **neutral is not
a safe group** — 184 trades, 57.1%, -$1,234.06 — and that the gate can only act
on the 70% of signals where the bias is decided.

This is why that 70% is not higher. The bias is not neutral because the market
is undecided; it is neutral because one wick vetoed an obvious downtrend.

## The decision

The remedies above are one-line changes, and each changes which trades are
taken:

1. **Compare closes, not wicks.** A wick is where price was rejected; a close
   is where it settled. Most trend definitions use closes for exactly this.
2. **Allow a tolerance** on the high/low comparison, so a 0.08% overshoot does
   not veto a 1.5% decline.
3. **Require either condition, not both.** Loosest, and would make far more
   signals "decided" — including some that should not be.
4. **Replace the structure test with a slope measure** over the window.

**Not chosen here.** Each widens what the gate blocks, which is a change to
live trading behaviour and belongs with the owner — the same reason blocking
`neutral` outright was left alone in
[090](../reversal-engine/090-level-score-bypasses-the-bias-filter.md).

**My reading, for what it is worth:** option 1 is the smallest change that
matches what every other measure of the same window already says, and it does
not need a new threshold chosen.
