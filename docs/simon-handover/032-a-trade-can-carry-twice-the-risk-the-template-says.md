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

---

## Addendum, 2026-09-14 — the same template, two stops, from two paths

You asked why these two look inconsistent:

```
2007286071   +$42.00   R 0.47      2007221685   +$41.56   R 0.83
```

Both "30 TP1 SL50 and Trail", both BUY, both 0.10 lot, both closed in the same
second. The profits are near identical; the R differs because the **risk**
differs, and only the risk:

| | 2007286071 | 2007221685 |
|---|---|---|
| signal | Telegram Auto, zone 4278–4282 | Telegram Instant, no zone |
| fill | 4290.86 | 4288.64 |
| stop at open | 4281.87 | 4283.65 |
| distance | **8.99 pts** | 4.99 pts |
| risk | **$89.90** | $49.90 |

R is profit / risk recorded at open, so 42.00/89.90 = 0.47 and
41.56/49.90 = 0.83. The R column is right. The stop distance is the story.

This is this file's issue, with two things the original write-up did not have:

**1. The gap-adjusted market entry makes the tail systematic, not a coin flip.**
The body above says "most fills land on the edge the stop is measured from".
That holds for a fill inside the zone. It cannot hold on the IME path. When
price has already left the zone, `scan_auto_execute` shifts the zone, the stop
and the ladder by the gap so the zone's **near** edge sits on the market — for
a BUY, `entry_high` becomes the market price. The stop is anchored to
`entry_low`. So the fill lands at the far edge from the stop **by construction,
every time**, and the risk is always `sl_pips + zone width`. Here: 5.00 + 4.00
= 9.00. Same shape on the SELL side (2003636700, 2-pt zone, 7.05 pts risked).

**2. Two execution paths disagree, on the same template and channel.**
`template_sl_at` — the function that re-measures a template's stop from the
actual fill reference — has exactly two call sites: `resolution.py` (the
`from_signal` path, used by PendingWatcher activations and manual entry) and
`limit_order_signal.py` (resting orders). The Telegram auto-execute path calls
`open_trade` directly with whatever stop the parser produced, so it never
re-measures. Live, 20 minutes after the trade above:

```
2007468045  PendingWatcher activation, 6-pt zone, fill 4286.20, stop 4281.17
            -> 5.03 pts, $50.30.   Re-anchored to the fill.
2007286071  Telegram auto-execute, 4-pt zone, fill 4290.86, stop 4281.87
            -> 8.99 pts, $89.90.   Zone-edge stop, passed straight through.
```

Same template, same day, 1.8x the risk, decided by which code path fired.

There is a related asymmetry inside `open_trade` itself: for a template it
re-resolves the whole **TP ladder** against the current tick
(`resolve_template_tps`) and passes the **stop** through untouched. The targets
move to the fill; the stop does not.

**Nothing here changes the options above.** Option B (measure the template's
stop from the fill) would close both gaps at once and is the same rule you
already chose for resting orders. Option D (show it) still costs nothing. The
new argument is that the IME path is not a tail case — every gap-adjusted entry
pays the zone width.

**ANSWER:**
