# 080 — The Telegram execution path has no trend filter

**Status:** open. **The single largest loss of 2026-09-08: -$718.95.**
**Money:** yes — it decides whether an order is placed.
**Found:** 2026-09-08, [data-inspect/004](../data-inspect/004-why-2026-09-08-lost-1270.md).

## What is missing

`governor.check_pre_trade_filters` applies exactly two gates:

1. minimum TP1 R:R
2. a directional cap on *concurrent unprotected* same-direction trades

Neither asks whether the higher timeframe is going the other way. So a channel
posting BUY signals into a sustained downtrend has every one executed.

On 2026-09-08, gold fell from 4438 to 4391 and `GOLD DIGGERS INSTITUTIONAL`
lost **-$718.95 over 20 trades, 5 wins to 15 losses**, almost all BUYs. The
directional cap limits how many run at once, not how many are taken in a day.

## The engine already computes what is needed

The Reversal Engine reads `htf_bias` per signal and uses it (imperfectly — see
[090](090-level-score-bypasses-the-bias-filter.md)). The Telegram path does not
consult it at all. **This is one signal, computed already, applied on one route
and not the other** — the same shape as the three independent copies of the IME
gate that bugs/024 was about, in reverse.

## What to build

A bias gate on the shared pre-trade path, so it applies to every source rather
than to whichever route remembers to ask. Decide with the owner whether it
blocks outright or only downsizes, because a channel he trusts may be
deliberately counter-trend.

**Measure before choosing the rule.** Today is one day. Before making this a
hard block, check across the full history whether counter-bias Telegram trades
lose in general or only lost today — `re_signals` carries `htf_bias`, and the
trade rows carry the source.

## Test first, then demo

It stops orders being placed. Tests before code, and it does not go live
without the owner watching.
