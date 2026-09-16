# 063 — The AI reviewer is told "ATR(M15)" and shown an M5 ATR

**Status: diagnosed, NOT fixed** (2026-09-16). **Currently inert** — the
Claude review gate is switched off on this install
(`bo_claude_eval_enabled`, "Claude eval OFF" in the log). Fixing it changes
what an AI gate is told, and that gate can veto a signal, so it wants the
owner rather than a quiet string edit.

Found while auditing the breakout engine's ATR column for the same fault
class as 060.

## The claim

The breakout engine computes one ATR, from **M5** candles:

```python
# breakout_signal_service.py:222  -> M5, 80 bars
m5_candles = await self._bridge.get_candles("M5", 80)
# :253
atr = compute_atr(m5_candles[-20:], period=14)
```

It stores it in a column named `atr_m15`, passes it to the AI reviewer under
the key `atr_m15`, and the prompt then states it as fact:

```python
# claude_reviewer.py:76
f"ADX: {adx:.1f}  |  MACD hist: {macd_hist:+.4f}  |  ATR(M15): {atr:.2f}",
```

The model is told a 15-minute volatility figure and given a 5-minute one.

## How wrong

Measured against the live bridge, 2026-09-16 20:50, over the same 300-minute
span:

| | |
|---|---|
| ATR(M5, 14) | 16.27 |
| ATR(M15, 14) | 19.93 |
| ratio | **0.82** |

So roughly a fifth low, at this moment. It is not a fixed ratio and it is not
the 3x a first guess suggests — a 20-bar M5 window and a 20-bar M15 window
also cover different amounts of time, which is a second reason the two
numbers are not interchangeable.

## What is and is not affected

**Not affected: every internal calculation.** `sl_dist_atr`,
`macd_momentum`, the ATR-collapse gate, `calculate_breakout_risk_levels` and
`barrier_fit`'s `atr` column all use the same M5 value consistently. They are
self-consistent and the name is the only thing wrong with them.

**Affected: the AI prompt**, which asserts a timeframe to a reader that has
no way to check it, and any human reading `atr_m15` in the database.

## What to do

1. The prompt line -> `ATR(M5)`. One word, no number changes. **This alters
   what the review gate is told and therefore what it may veto**, so it is
   the owner's call and wants a demo session if the gate is turned back on.
2. The column name is legacy and should stay. Renaming a live column on 124
   rows buys nothing that a line in `domains/engines/README.md` does not.

Same family as 059, 060 and 062: a number derived from one thing and
presented as another, with nothing in the code connecting the label to the
source.
