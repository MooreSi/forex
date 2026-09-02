# 025 — Global harvest does nothing without the EA, and only covers one symbol

**Decision needed:** yes, for the second half.
**Money:** yes — it closes live positions.
**Found:** 2026-09-02, investigating item 3 of your list.

## What you reported

> "trading > strategy > global parameters - harvest figure is set and the
> toggle is on but it doesn't appear to monitor the ea or mt5 for all trades
> that are live and action based on the figure set"

Correct on both counts, for two separate reasons.

## Why nothing is harvesting right now

**The EA is not attached.** Checked live:

```
EA effective status : False
EA healthy          : False
secs since last seen: None
```

Global harvest is implemented **entirely in the EA** —
`CheckGlobalHarvest()` in `ForexTraderBridge.mq5`, called from `OnTick`. The
Python side is correct and I found no fault in it: saving the setting writes
`global_harvest_enabled` / `global_harvest_threshold_usd`, and
`push_global_config()` sends them to the EA both when you press Save and on
every EA hello. With no EA on a chart there is nothing to receive that push
and nothing to check the threshold.

You removed the EA from the chart during the demo session on 2026-09-01 and it
has not been re-attached. **Re-attaching it should restore harvesting** — no
code change needed for this half.

## The part re-attaching will NOT fix

```mql5
if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
```

The EA only harvests positions **on its own chart symbol**. An EA attached to
XAUUSD cannot see a EURUSD position, so "all trades that are live" is not what
it does today — it is "all trades on this chart's symbol".

There is also no Python-side fallback. Basket harvest has one
(`core_equity_protect.check_basket_harvest`, wired into the monitor cycle);
global harvest has none, which is why it fails completely rather than
degrading when the EA is absent.

## What I did not do

I have not changed any of it. Making harvest genuinely cover every live trade
means a Python-side monitor that closes positions when their profit crosses
the threshold — which is the money path, and under your own rules that needs
your sign-off and a demo session. It also overlaps the frozen close path.

## What I would suggest, when you want it

1. **Re-attach the EA first** and confirm harvesting works on XAUUSD. That
   costs nothing and tells us the existing path is sound.
2. Then decide whether you want the Python-side monitor for other symbols. If
   you only ever trade XAUUSD, you may not need it at all — in which case the
   honest fix is to relabel the setting so it stops promising "every open
   position".

That relabelling is the one part I could do without a demo, and I have left it
alone only because it is your wording to choose.
