# What "Enable SL Parsing OFF" actually costs per trade

**Measured 2026-09-10 from 41 live replacements.** Not a bug — this is the
configured behaviour working exactly as designed. It is written down because
the **magnitude** bears directly on the payoff problem, and it is not visible
anywhere on screen.

## The measurement

With the toggle off, `apply_sl_parsing_override` discards the channel's stated
stop and derives one from the template's `sl_pips`, anchored to the far edge of
the entry zone. Across every replacement in the current log:

| | |
|---|---|
| replacements | **41** |
| widened the stop | **39** |
| tightened it | 1 |
| unchanged | 1 |
| **mean change** | **+1.68 points** |
| mean of those widened | **+4.31 points** |

At the fixed 0.10 lot, a point of gold is $10. So the average widened trade
carries about **$43 more risk than the channel intended**, and the mean across
all replacements is **+$17**.

## What the channels actually post

Verified against raw message text, because the first reading of this was wrong
— a 190-character truncation made it look as though the channels stated no stop
at all:

```
Direction  BUY          Direction SELL
ENTRY : 4359- 4355      ENTRY : 4360-4358
🛑 SL:  4353            🛑 SL:  4365
```

Two points below the zone, and five above it. **The stated stops are real**,
and they are tight: across the 41 replacements the channel's stop sat 1 to 5
points from the zone edge, against the template's 5 or 7.

## The trade-off, both ways

**For the template's wider stop:** a 1-2 point stop on gold is inside the
noise. It would be taken out constantly, and the one replacement that
*tightened* shows the other failure mode — a channel posting a stop 104 points
away, which the template correctly overrode.

**Against it:** losses are the profitability problem, not win rate.
[reversal-engine/020](../todo/reversal-engine/020-losses-exceed-the-stop.md)
measures losses at -1.161R against wins at +0.642R, and break-even at 64.4%
against an actual 59.4%. Widening every stop by 4.31 points makes each loss
correspondingly larger — 2026-09-10's losses ran -$44.93, -$49.60, -$50.60,
-$51.80, -$59.50, -$69.80, all consistent with 5-7 point stops rather than the
1-2 point ones the channels posted.

**And the targets move too.** `30 TP1 SL50 and Trail` sets `tp1_pips=40`, four
points, where the channel's TP1 was two. The template does not just widen the
stop; it converts a scalping signal into a wider-stop, wider-target trade. That
may well be right — the channels' own record is not obviously better — but it
is a different strategy from the one the signal describes.

## Not a recommendation

There is no measurement here of which shape makes more money, and this file
does not claim one. What it establishes is the size of the difference, so the
choice is made knowing it: **turning that toggle off adds roughly $43 of risk
to a typical trade.**

The comparison worth running, once
[020](../todo/reversal-engine/020-losses-exceed-the-stop.md)'s `last_seen_sl`
data has accumulated, is realised R under the template stop against what the
same trades would have returned on the channel's own stop.
