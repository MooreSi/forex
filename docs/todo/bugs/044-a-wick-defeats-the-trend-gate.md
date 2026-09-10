# 044 — A 3.53-point wick turns the trend gate off

**Status:** **FIXED 2026-09-10 on the owner's instruction** ("make the change,
we need better risk management and improved profitability"). Option 1: closes,
not wicks. See "What shipped" at the end.
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


---

## What shipped

`get_htf_bias` compares the highest and lowest **close** of each half instead of
the highest wick and lowest wick. The live case that found this — a 41.84-point
decline vetoed by a 3.53-point wick — now reads **bearish**, which blocks BUYs.

**This deliberately widens what the gate blocks.** More windows are now
"decided", which is the point: [080](../reversal-engine/080-no-trend-gate-on-the-telegram-path.md)
measured that the gate could only act on 70% of signals, and a good part of the
other 30% was a wick vetoing a real trend.

### Two things the existing tests caught that I had wrong

**A missing `close` would have switched the whole gate off.** Six tests in
`test_level_detector.py` build candles as bare `{"high": .., "low": ..}`. The
first version read the absent close as `0.0`, which makes every window neutral
— and neutral does not block. It now **falls back to wicks** when closes are
absent or zero, rather than to zero, and that fallback is pinned in both
directions plus the partial-payload case.

**Both conditions are still required.** A mutant loosening `hh and hl` to
`hh or hl` survived the first pass, because nothing distinguished them. An
**expanding range** does: a higher high *and* a lower low is genuinely
undecided, and calling it a trend would have the gate blocking inside a
widening range — the over-refusal the runbook warns about. Pinned both ways.

Three mutants die: reverting to wick highs, either-instead-of-both, and moving
the split point.

### Not changed

The H4 weighting block below the structure test still uses wicks. It never runs
on the gate's path — `governor.current_htf_bias` calls `get_htf_bias(candles)`
with H1 only — so changing it would alter callers that were not the subject of
this, with no measurement to justify it.


---

## Does it suppress Asian-hours trading? No. (measured 2026-09-10)

The owner asked, because the engine has historically profited overnight in
Asia. Both rules were run over **680 rolling 20-bar windows**, 2026-07-30 to
2026-09-10, bucketed by session:

| session | bars | old decided | new decided | change |
|---|---|---|---|---|
| **asian** | 238 | 169 (71%) | 169 (71%) | **±0.0 pts** |
| london | 120 | 86 (72%) | 87 (72%) | +0.8 |
| overlap | 150 | 121 (81%) | 125 (83%) | +2.7 |
| ny | 172 | 143 (83%) | 149 (87%) | +3.5 |
| all | 680 | 519 (76%) | 530 (78%) | +1.6 |

**Asian hours are exactly unchanged** in how often the gate has an opinion. The
extra decisiveness lands in NY and the overlap, where trends actually run.

### The net figure hides real movement, so: it disagrees 18% of the time in Asia

It loosens about as often as it tightens there:

* `bullish -> neutral` x15 — now PERMITS trades it used to block
* `neutral -> bearish` x12 — now blocks trades it used to permit
* `neutral -> bullish` x7

Across the whole sample the dominant change is **`neutral -> bearish`, 52 of
127 disagreements** — windows where price was genuinely falling and a wick
masked it. That is the fault this file is about, and it concentrates in the
trending sessions.

Outright direction flips are almost absent: `bullish -> bearish` 4 times in
680 windows, `bearish -> bullish` twice.

### What this does NOT show

How often the gate is *right*. It measures whether it has a view, not whether
the view makes money, over six weeks of one instrument in one regime. The
measurement to repeat is 080's blocked-versus-executed comparison, which will
now include windows that used to be neutral.
