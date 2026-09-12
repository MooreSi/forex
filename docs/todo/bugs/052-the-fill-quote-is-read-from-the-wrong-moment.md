# 052 — The quote a fill is measured against may be from another part of the day

**Status:** found 2026-09-12 from `execution_quality`. **Half fixed the same
day:** the broker/drift decomposition now refuses a quote that is not from the
fill's moment, and says so in the log. The spread read from that same tick is
deliberately **left alone** — see *What was not changed*.
**Touches money:** not directly. It is a measurement, and one of its outputs
feeds the meta-label gate, which is why the second half waits for the owner.
**Severity:** the numbers look precise to three decimals, are printed in the
nightly research report, and on every occasion they have run they have been
impossible.

## The four measurements

`broker_slippage_pts` and `entry_drift_pts` shipped recently, so only four
trades have ever been decomposed. All four are from 2026-09-11, all four are
**market** orders, and all four are impossible:

| requested | fill | real slippage | broker slippage | entry drift | spread | stop |
|---|---|---|---|---|---|---|
| 4371.54 | 4371.54 | **0.00** | +35.91 | -35.91 | 0.21 | 4.72 |
| 4370.50 | 4372.13 | 1.63 | +37.15 | -35.52 | 0.22 | — |
| 4370.50 | 4371.20 | 0.70 | **+72.46** | **-71.76** | 0.26 | — |
| 4361.42 | 4361.90 | 0.48 | -23.53 | +24.01 | 0.22 | 5.36 |

A market order fills at the quote. A 72-point gap between the fill and "what
the broker was quoting at that instant", on an instrument whose spread is 0.22
and whose stop here is under five points, does not happen.

The two halves are large, equal and opposite because they are **defined** to
sum to the real slippage. That is the signature of a bad reference price, not
of real drift: the split is measuring two different moments and the error
cancels in the total.

## Where the reference price comes from

`tca.measure` asks `bridge.get_tick_at(open_time)`, which is
`mt5_bridge._get_tick_at`:

```python
ticks = mt5.copy_ticks_from(SYMBOL, from_dt, 1, mt5.COPY_TICKS_ALL)
```

Two candidate explanations, and this repo has already been bitten by the
second:

1. **`copy_ticks_from` returns the first tick AT OR AFTER the timestamp**, with
   no bound on how far after. Across a gap — a weekend, a session break, a feed
   outage — that is the next tick whenever it arrives.
2. **MT5 reads timestamps in its own server convention.**
   `mt5_bridge._get_candles_range` carries a comment from 2026-07-07 saying
   exactly this, discovered by direct testing, and it *"was feeding wrong price
   data into `_tp_safety_net_check_trade` (bogus 'extreme reached'
   determinations)"*. A UTC+3 broker moves the reference three hours; gold
   moves 35 points in three hours without trying.

The tick already carries its own `time`. Nothing looked at it.

## What was fixed

`tca._tick_is_contemporary`: if the returned tick's `time` is more than
`MAX_QUOTE_AGE_S` (30s) from the moment asked about, the broker/drift split is
left **unmeasured** and a warning names the gap. Ticks here are sub-second in an
active session, so thirty seconds is ordinary spacing and anything past it is
another part of the day.

A tick with no `time` is used exactly as before: every tick the real bridge
returns carries one, and refusing those without it would delete the measurement
wherever the field is absent rather than wherever the quote is wrong.

The published `slippage_pts` and the spread are untouched by the refusal, and a
test asserts that — refusing the split must not quietly blank the numbers
already being reported.

**The warning is the point.** The next measurement now says how far off the
quote was, which decides between explanation 1 and explanation 2 without
anybody guessing.

## What was NOT changed, and why it is the owner's

`spread_open_pts` and `spread_close_pts` come from the **same possibly-wrong
ticks**. A spread from the wrong hour still looks like a spread — that is
exactly why this hid until someone started using the price from that tick — so
`cost_pts` and `cost_r` on all 293 rows may be built on quotes from elsewhere.

Blanking them is not a tidy-up: `cost_r` feeds `meta_label`, whose gate can
refuse trades, and narrowing that dataset changes what the gate learns from.
That is his call, and it should be taken after the warning above has produced
one live measurement saying how far off these quotes actually are.

## The other half of this table is missing entirely

`fill_delay_s` is **NULL on all 293 rows**. `tca.measure` computes it only when
handed a `decision_ts`, and its only caller — `research_lab.measure_pending` —
does not pass one.

That matters this week: the owner turned the **minimum fill delay** on
(`min_fill_delay_s`, `governor.py`). The column that would show whether it
changes anything has never recorded a single value. Wiring it up means choosing
what "the decision moment" is for each route, which is a judgement rather than a
patch, so it is filed here rather than guessed at.
