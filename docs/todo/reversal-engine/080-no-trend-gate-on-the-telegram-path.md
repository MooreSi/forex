# 080 — The Telegram execution path has no trend filter

**Status:** **BUILT 2026-09-09, off by default, NOT DEMOED.** Turn it on at
Trading > Strategy > Risk Settings, "Only trade with the trend".
**The single largest loss of 2026-09-08: -$718.95.**
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


---

## Built 2026-09-09 — and the diagnosis above was incomplete

**This file said the Telegram path had no TREND filter. It has no pre-trade
filter at all.** `resolution.py` guards the whole block:

```python
if strategy not in _self_level_strategies and not _is_template:
    filter_err = check_pre_trade_filters(...)
```

**Every trade that lost money on 2026-09-08 was a template strategy**
(`template:GD Instituational - single`, `template:30 TP1 SL50 and Trail`), so
the R:R minimum and the directional cap did not run on them either. A bias gate
added inside `check_pre_trade_filters` — the obvious place, and where this file
originally pointed — **would not have stopped a single one of them.**

The gate is therefore its own check, deliberately outside that condition, and a
test asserts its position relative to `and not _is_template` so it cannot be
quietly moved back inside.

### The measurement this file asked for, done first

Across every executed Reversal Engine signal on record, not just 2026-09-08:

| | n | win % | net |
|---|---|---|---|
| with the bias | 369 | 61.8 | **+$101.41** |
| against it | 201 | 56.2 | -$1,210.98 |
| neutral | 184 | 57.1 | -$1,234.06 |

**Trading with the bias is the only profitable group in the entire history.**
So the rule generalises; it was not a one-day artefact.

### What shipped

`governor.htf_bias_blocks(direction, htf_bias, rs)` — one function, called from
the shared open path AND the Reversal Engine, with a test asserting both use it
rather than growing a second copy.

`governor.current_htf_bias(bridge, rs)` supplies it, cached 60s, and **makes no
bridge call at all while the toggle is off**. It delegates to
`level_detector.get_htf_bias`, the implementation whose recorded output is the
evidence above. (There is a second implementation in
`test_signal/signal_generator.compute_htf_bias`; they must not both become
"the" bias.)

**Off by default** (migration 35, `htf_bias_gate_enabled`), so nothing changes
until the owner turns it on. **Not demoed** — it refuses orders that would
otherwise be placed.

**Neutral does not block**, though it loses as much as counter-bias does. "No
clear trend" is a different claim from "the trend is against you", and blocking
184 trades' worth is a bigger change than was asked for. See
[090](090-level-score-bypasses-the-bias-filter.md).
