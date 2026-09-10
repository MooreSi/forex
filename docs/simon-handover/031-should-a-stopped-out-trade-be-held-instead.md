# Should a stopped-out trade have its stop widened instead of being closed?

**Status:** open, **needs your decision**. Nothing has been changed.
**Money:** yes — it is the stop, the position size and the halts, all at once.

**The question, as you asked it on 2026-09-10:** ticket 1985529729 hit its stop
for -$45 and a new trade in the same direction opened seconds later. The
direction was right and only the stop was wrong. Would it have been better to
hold the position, widen the stop, and stay in? And should that be a toggle?

**The short answer: no, not as a post-entry widen — and in that specific trade,
holding would have been the worse trade.** The data says so, and the reason is
not obvious. What is worth doing is a different change, described at the end.

## The two tickets

| | 1985529729 | 1985645713 |
|---|---|---|
| Direction | SELL | SELL |
| Entry | 4322.70 | **4327.94** |
| Stop | 4327.20 (4.50 pts) | 4327.94 (at breakeven) |
| Held | 14m 55s | still open at time of writing |
| Result | **-$45.00** | **+$33.00 realised**, 0.02 lots running |

The replacement went short **5.24 points higher** than the trade that was
stopped out. That is the whole point. Widening the stop and staying short from
4322.70 would have meant sitting through that entire 5.24-point excursion, and
the position would be roughly flat now, where the re-entry is +$33 with a free
runner. The stop-out plus re-entry did not cost $45 against holding; it bought
a materially better price for it.

## It is not a one-off

Measured over the whole demo history in `forex_trader_demo_26004592.db`,
**2026-09-03 to 2026-09-10**, 255 closed trades.

Of the 132 genuinely losing stop-outs, 91 were followed by a same-direction
re-entry inside 30 minutes:

| | |
|---|---|
| pairs measured | **91** |
| re-entry got a **better** price | **80 (88%)** |
| mean improvement | **5.55 points** |
| mean stop distance on the original | **5.98 points** |
| improvement **larger than the whole stop** | **51 of 91** |
| range | -15.53 to +14.05 points |

**Read the third and fourth rows together.** The average adverse excursion
after entry is about the size of the entire stop, and in 51 of 91 cases price
ran further against the original entry than the stop was wide *before* it
turned. On those trades a "widen and hold" rule holds a losing position through
an excursion bigger than the risk that was signed off, to end up in a worse
position than the re-entry took anyway.

The worst examples are the clearest. On 2026-09-10 06:14 a BUY stopped out at
4428.76 for **-$101.56**; the two re-entries went long at 4415.18 and 4413.95
and both made money. Holding the 4428.76 entry through that would have been the
single most expensive decision in the sample.

### Re-entry is not free either

The same 91 re-entries netted **-$568.18** with only **51 winners**. Re-entry
is better than holding a bad price. It is not better than not trading. That is
a separate question and there is currently no cooldown or per-signal re-entry
cap after a stop-out.

## Why I would not offer post-entry widening as a toggle

Four reasons, in order of severity:

1. **It silently breaks position sizing.** Lot size is derived from the stop
   distance. Move the stop after the fill and the position is sized for one
   risk and carrying another. `initial_risk = 45.0` on that row becomes fiction,
   and every downstream R figure with it — including
   [020's](../todo/reversal-engine/020-losses-exceed-the-stop.md) loss-per-R
   measurement, which is the most important number on the list.
2. **It disarms the halts.** `rg_check_halt`, the daily loss limit and the
   circuit breaker all count **realised** losses. A loser you refuse to close
   never counts. The protection goes quiet exactly when it is needed, and the
   worse the day, the quieter it gets.
3. **The tail is unbounded and the account is not big.** Equity was **$801.49**.
   That one trade was already 5.6% of it. With 202 of 255 exits coming at the
   stop, one position with a retreating stop can end the account.
4. **It inverts the domain's failure direction.** Risk "never places or
   modifies orders itself, and its failure direction is refuse-to-trade"
   (`docs/system/domains/risk/README.md`). Widening under pressure is the
   opposite direction, and it is the direction that does not recover.

## What the evidence actually supports

Your diagnosis is right. The stop is too tight. The lever is wrong.

`30 TP1 SL50 and Trail` sets **`sl_pips = 50`, a fixed distance**, with no
reference to volatility. It accounts for 98 of the 132 losers and -$5,012 of
the -$6,611. The average adverse excursion after entry, measured above, is 5.55
points. The stop is parked just inside the noise band, so it is hit by noise,
and the direction is then vindicated a few minutes later. That is exactly the
pattern you spotted.

**Option A — volatility-scaled stop, fixed dollar risk (recommended).**
Replace the fixed `sl_pips` with an ATR multiple and reduce lots so the dollar
risk stays where you set it. Same $45 at risk, roughly twice the room. Nothing
about the halts, the sizing arithmetic or the R accounting changes, because the
stop is still decided once, before the position is sized.

The machinery is half-built already. `rg_max_stop_atr`
([governor.py:106](../../backend/src/services/risk/governor.py)) caps stops
that are too **wide**; `sl_mult` / `sl_cap_pt` / `sl_floor_pt` in
[strategy_params.py](../../backend/src/services/risk/strategy_params.py) shape
Reversal Runner's and Adaptive Runner's stops the same way. There is no floor
for a stop that is too **narrow**, and the EA templates do not go through that
path at all. That is the gap.

Note this pulls in the opposite direction from
[030](030-what-sl-parsing-off-costs-per-trade.md), which measured the template's
override *adding* about $43 of risk per trade against the channel's own stop.
Both can be true: the template's stop is too wide for what the channel sent and
too narrow for what gold actually does. Deciding this properly means deciding
the trade shape, not just the number.

**Option B — re-entry cooldown or cap.** Independent of A, and safe: after a
stop-out on a signal, refuse or delay a same-direction re-entry. The -$568 over
91 re-entries says the current unlimited behaviour is not paying for itself.

**Option C — use the commentary that is already being written.** Claude's open
commentary on 1985529729 scored it **0.38 setup quality, 0.78 risk** and said
in advance that the stop "is likely to be swept before the downside resumes",
naming 4332.94 as the structurally safer level. It was right. That score is
computed on every trade, stored, and used for nothing.

## What I need from you

1. Confirm that post-entry stop widening is **off the table** as a feature, or
   tell me the constrained form you would accept.
2. Choose between A, B, C, or a combination.
3. If A: the ATR multiple and the floor, or agreement that I propose values
   from the measured excursion distribution first.

**Any of these touches sizing and the risk governor, so none of it gets
implemented without your sign-off and a demo session.** Saying "go ahead" to
this document is not that sign-off.

## Caveat on the measurement

This compares **entry prices** across 91 pairs. It is not a tick-level replay
of what a held position would have done, because the excursion data
(`mae_pts`) that would allow one is still accumulating — see
[020](../todo/reversal-engine/020-losses-exceed-the-stop.md), blocked on data
until roughly 2026-10-01. The direction of the finding is not in doubt at 80
out of 91. The exact cost of holding is not established, and this file does not
claim it is.
