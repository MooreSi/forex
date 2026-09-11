# 032 — A trade can carry twice the risk its template says, and nothing shows it

**Status:** open, **for your decision**. Nothing has been changed.
**Money:** yes — it is the size of a losing trade.
**Found:** 2026-09-11, working backwards from one -$120.30 stop-out on your
account this morning, on a day where every other loss was about -$50.

## The trade that started it

```
05:23  SELL  GOLD DIGGERS INSTITUTIONAL   template "GD Instituational - single"
       entry zone   4325.13 - 4330.13
       filled at    4325.10
       stop         4337.13
       closed       4337.13   -$120.30
```

Nothing malfunctioned. The stop was honoured exactly, to the penny, and the
app recorded the risk correctly after the fact. The loss is **precisely** what
that trade was set up to risk.

The point is that nothing told you it was set up to risk it. The template says
`sl_pips: 70` — seven points, **$70** at your fixed 0.10 lot. This trade risked
**$120.30**.

## Where the other $50 came from

With **Enable SL Parsing off** (your setting, confirmed yesterday), the app
ignores the channel's stop and derives one from the template. It anchors that
distance to the **far edge of the entry zone** — deliberately, and for a good
reason: it guarantees the stop sits beyond the whole zone whatever price the
fill happens at, so the signal always passes its own validity checks.

The consequence is arithmetic:

```
risk = the template's distance  +  how far the fill was from the far edge
```

Fill at the edge the stop is measured from, and you risk exactly what the
template says. Fill at the other end of a five-point zone, and you risk the
template's seven points **plus** those five.

This morning's trade filled at the far end of a five-point zone. 7 + 5 = 12.03
points = $120.30.

## How often, measured over 14 days

261 template trades on your account:

| | "30 TP1 SL50 and Trail" | "GD Instituational - single" |
|---|---|---|
| trades | 210 | 51 |
| the template says | 5.0 pts = **$50** | 7.0 pts = **$70** |
| median actually risked | **$50.00** | **$70.60** |
| 90th percentile | $56.90 | **$121.70** |
| worst | $116.60 | $130.20 |
| carried more than the template says | 72 (34%) | 28 (**55%**) |

**The typical trade is fine.** The median trade on both templates risks exactly
what the template states, because most fills land on the edge the stop is
measured from — 111 of 186 zoned fills landed at the better end, which is also
the stop-adjacent end. This is a tail, not the norm, and it would be wrong to
read the table as "every trade risks double".

But the tail is not small on the Institutional template, where **more than half**
carry extra and the 90th percentile is nearly double the stated risk.

**Across both templates, 22 trades (8%) carried at least 1.5x the template's
stop.** Sixteen of them were stopped out, for -$696.35; eight won, for +$398.98;
net **-$433.85**.

## What it costs, stated carefully

Summing, over every stopped-out trade, the part of the loss beyond what the
template's own distance would have cost:

| | |
|---|---|
| "30 TP1 SL50 and Trail" | $447.30 |
| "GD Instituational - single" | $630.00 |
| **total, 14 days** | **$1,077.30** |

Against -$3,833.48 net across those 261 trades, that is **28% of the loss**.

**That is not $1,077 of profit forgone, and I am not claiming it is.** A tighter
stop would have been hit *more* often, not less — some of those trades would
have been stopped out that instead went on to win. The honest statement is
narrower: **$1,077 is extra risk that was taken and realised, beyond the number
on the template.** What a tighter stop would have netted is a different
question, and it needs the excursion data that is still accumulating
(`docs/todo/reversal-engine/020`).

## Why this is a decision and not a bug report

**You have already decided this exact question once, the other way.** On
2026-09-10, for resting limit orders, you chose that a template's stop is
measured **from the resting price** rather than from the tick — and the reason
recorded with that answer was:

> "the stop ends up 60 pips from where the trade actually opens. This is what
> the template means, and it makes a limit order's risk identical to the same
> template's risk on a market fill."

The last clause assumes a market fill already risks the template's distance.
For the tail above, it does not. So the principle you chose for limit orders is
**not** what the market path does today.

## Your options

- **A. Leave it.** The stop is guaranteed to clear the zone, validation is
  simple, and the median trade is unaffected. The price is that risk per trade
  varies by up to 2.4x with no warning.
- **B. Measure the template's stop from the fill price**, the same rule you
  chose for resting orders. Every trade then risks what the template says.
  **The catch, and it is why this is not obviously right:** on a fill at the
  unfavourable end of the zone, the stop then sits *inside* the zone the signal
  named as its entry area — a stop where the channel expected price to trade.
  It would be hit more often.
- **C. Keep the anchoring, size the lot to the risk.** The stop stays where it
  is and the lot shrinks when the fill is far from it, so the dollar risk is
  constant. This is what "Risk per trade %" already does; it is off, because
  Fixed Lot Size is 0.10. It changes every trade's size, not just the tail.
- **D. Show it.** Leave the behaviour alone and put the actual risk on screen
  and in the Telegram alert when it exceeds the template's number. Fixes
  nothing, hides nothing, and costs no money either way.

**Recommended: D now, then decide between A and B once
[reversal-engine/020](../todo/reversal-engine/020-losses-exceed-the-stop.md)
unblocks.** D is the only one that is not a money-path change, and 020's
excursion data is what would settle whether a tighter stop pays — which is
exactly the question B turns on.

**ANSWER:**

## What was checked, and what was not

Checked, read-only, against `forex_trader_demo_26004592.db`:
the 261 trades, their zones, their stops at open (`initial_sl`, so EA trailing
cannot distort it), the two templates' `sl_pips`, and where in each zone the
fill landed.

Not checked: whether the same holds on the Reversal Engine's own path, which
does not use these templates and is measured separately in
[reversal-engine/020](../todo/reversal-engine/020-losses-exceed-the-stop.md).
That file finds losses **exceeding** the stop; this one finds losses landing
exactly on a stop that is wider than expected. They are different faults on
different paths and neither is evidence for the other.
