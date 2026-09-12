# 041 — A profitable Global Harvest pushes the circuit breaker toward a halt

**Status:** **ANSWERED 2026-09-11, fully specified.** Owner: *"a harvest
shouldn't trip or count towards the breaker"*, then **B** on the follow-up — a
losing leg is invisible, a **winning basket still clears the counter**.
**NOT BUILT**, and it cannot be built entirely on this side: the EA has to say
which closes were a harvest. See *The spec* at the bottom.
**Money:** yes. It halts live trading.
**Found:** 2026-09-09, from the live demo account. Complete evidence below.

## What happened, on the clock

Global Harvest banked a **winning** basket:

```
20:19:15 [EABridge] global harvest threshold reached
                    (combined $78.1 >= $75.0 across 4 position(s)) -- closing all
20:19:15   closing ticket=1973249365 ($39.3)
20:19:15   closing ticket=1973242032 ($38.4)
20:19:15   closing ticket=1973240300 ($32.2)
20:19:15   closing ticket=1973182186 ($-31.1)   <- the losing leg, closed LAST
```

Net **+$78.10**. Then:

```
20:36:25  manual close   -$2.42
21:16:17  stop loss      -$48.80
21:16:17  [CB] Circuit breaker triggered — live trading blocked for 15 min.
```

The breaker is set to **3** consecutive losses. Only **two** losses follow the
basket. It fired, so the counter must have stood at **1** when the basket
finished — meaning the harvest's losing leg was counted as a consecutive loss,
and the three winners that were closed in the same action did not cancel it.

## Cause

`circuit_breaker_repo` counts **per closed trade**:

```python
if won:
    update_risk_settings({"circuit_breaker_consec_losses": 0})
else:
    consec += 1
```

A basket close calls it once per leg. Whether the counter survives depends on
which leg the EA happens to close last, and `CheckGlobalHarvest` walks
`PositionsTotal()` downward — so it is position index order, not anything
meaningful.

**So the same harvest, with the same profit, can leave the counter at 0 or at
1 depending on the order the positions happen to sit in.**

## Why it matters

Global Harvest exists to bank a **combined** total, explicitly including legs
that are individually losing — that is stated in `CheckGlobalHarvest`'s own
comment and in demo 8. Counting one of those legs as a "consecutive loss" then
moves the account toward a trading halt as a consequence of a **profitable**
action. Two ordinary losses afterwards were enough to stop trading for 15
minutes.

## The decision

1. **A harvested leg does not touch the breaker.** The basket was an
   account-level action, not a per-trade outcome.
2. **The basket scores once, on its net.** +$78.10 is a win, so the counter
   resets — arguably what a "consecutive losses" counter means.
3. **Leave it.** A losing leg is a losing trade, and the breaker is
   deliberately blunt.

**2 looks right and is not being applied**, because it changes when live
trading halts, and that is the owner's call. The same question applies to
`equity_protect` and `check_basket_harvest`, which also close several
positions in one action.

## Related

* [027](027-global-harvest-was-per-trade-not-a-basket-total.md) — the harvest
  itself, verified working live the same day (twice).
* Demo 8 in the runbook.


---

## Confirmed a second time, 2026-09-10 11:35 — and this one is starker

```
10:46:04  harvest closes five positions:
            +$42.49  +$24.20  +$19.20  +$22.10  -$0.80
          net +$107.19
11:33:24  SL  -$49.80
11:35:33  SL  -$52.50
11:35:33  [CB] Circuit breaker triggered — live trading blocked for 15 min.
```

The threshold is **3** and only **two** real losses occurred after the harvest.
So the counter stood at 1 when the basket finished: **the -$0.80 leg counted as
a consecutive loss.**

**An eighty-cent leg inside a $107 winning basket halted live trading fifty
minutes later.**

The first occurrence (2026-09-09, -$31.10 inside a +$78.10 basket) could be read
as a real loss of a real size. This one cannot. The leg is a rounding error
against the basket that closed it, and it still cost a fifteen-minute halt.

### It is specific to a MIXED basket

The 09:43 trip the same morning was **not** this bug: that harvest closed two
positions, both winners, the counter correctly reset, and three genuine
consecutive losses tripped it. So the counting is right whenever the basket has
no losing leg — which isolates the fault precisely to a basket that mixes them.

That also rules out "the breaker is simply too sensitive" as an explanation for
either trip.

### What it costs

Two halts in under two hours on 2026-09-10, of which **one was caused by this**.
Each is fifteen minutes of no live execution, and the day was net positive
(+$1.62 across 27 closes) while it happened.


---

## What option 1 needs (2026-09-11)

### 1. Nothing can currently tell that a close was a harvest

Traced end to end. The EA closes each leg with `trade.PositionClose(ticket)`
inside `CheckGlobalHarvest` and sends **no** marker with it. The reason string
that reaches Python is derived afterwards, in the generic detector at
`ForexTraderBridge.mq5:3078`, by reading the last deal's comment:

```
if      comment contains "tp" -> reason = "TP"
else if comment contains "sl" -> reason = "SL"
else                          -> reason = "MT5_close"
```

A harvested leg therefore arrives as **`MT5_close`** — the same string as a
position closed by hand in the MetaTrader terminal. There is no way to tell
them apart from Python, and inferring it (*"several closes landed in the same
second"*) would be guesswork that misfires on a busy minute.

**So this needs an EA change:** `CheckGlobalHarvest` marks the tickets it is
about to close, and the detector reports those as `global_harvest`. That is a
new EA version, `tools/deploy_ea.sh`, and F7 in MetaEditor — the same loop as
EA 1.07.

### 2. The Python half is one line, inside the frozen close path

`record_close` (`services/trading/close_trade.py:339`) calls
`record_live_trade_outcome(won=...)` for every close with an `mt5_ticket`. The
change is to skip that call when the reason is `global_harvest`. One condition
— but `record_close` is on the frozen list (golden rule 4), so it ships with a
demo session, not overnight. The same applies to `equity_protect` and
`check_basket_harvest`, which also close several positions in one action and
would want the same marker.

### 3. One consequence to confirm, because "doesn't count" cuts both ways

Today a basket's legs each score individually, so a basket of **winners resets
the counter** — that is what happened at 09:43 on 2026-09-10, correctly.

Under option 1 the breaker cannot see a harvest at all, so:

* a losing leg no longer pushes you toward a halt — the fault, fixed; **and**
* a **winning** basket no longer clears the counter either.

Recorded as **invisible in both directions**, because that is what "shouldn't
count towards the breaker" says. If you would rather a profitable basket still
clear the counter — bank the winners, reset the streak — that is a one-word
change to the spec and should be said before it is built.

**ANSWER 2026-09-11: B — invisible for losses, still clears on a winning
basket.**

---

# The spec

## Behaviour

For a close whose reason is `global_harvest`:

| the basket | the consecutive-loss counter |
|---|---|
| net profit >= 0 | **reset to 0** |
| net profit < 0 | **untouched** — no increment, no reset |

and an individual leg never scores on its own, whichever way it went. So the
-$0.80 leg inside the +$107.19 basket does nothing, and the +$107.19 clears the
streak once.

**"Net" means the basket, not the leg.** That is the whole point of the
decision, and it is also the hard part: the legs arrive as separate closes,
one message each. Whatever is built has to know they belong together and what
they summed to.

## Three pieces, in order

**1. The EA marks its own harvest closes.** `CheckGlobalHarvest` already knows
the combined total (`GlobalHarvestFloating`) and the exact set of tickets it is
about to close. It must carry both across: a reason of `global_harvest`
instead of the generic `MT5_close`, plus the basket's net and a basket id so
the legs can be tied together on this side. That is a new EA version,
`tools/deploy_ea.sh` and F7 — the same loop as EA 1.07.

Without this there is nothing to build on: a harvested leg is currently
indistinguishable from a position closed by hand in the terminal.

**2. The breaker call learns the reason.** `record_close`
(`services/trading/close_trade.py:339`) calls
`record_live_trade_outcome(won=...)` for every close carrying an `mt5_ticket`.
It needs to skip that call for a harvested leg, and instead score the basket
**once**, on its net, when the last leg of that basket arrives.

`record_close` is on the frozen list (golden rule 4), so this ships with a demo
session.

**3. The same marker for the other two basket closers.**
`equity_protect` and `check_basket_harvest` also close several positions in one
action and have the identical problem. They should use the same mechanism
rather than a second one.

## How it gets demoed

Demo 8 already drives a Global Harvest on the demo account. This extends it:
open a mixed basket (at least one leg in loss), harvest it, and read
`circuit_breaker_consec_losses` before and after.

* **Pass:** a mixed basket that nets positive leaves the counter at **0**; a
  mixed basket that nets negative leaves it **unchanged** from before.
* **Fail:** the counter moves by the number of losing legs — today's behaviour.

## What it is worth

Two halts in under two hours on 2026-09-10, one of them caused by this. Each
is fifteen minutes with no live execution, and the day was net positive while
it happened.

---

## Why this did not get built on 2026-09-12

Picked up under "fix everything you can". It is the only unbuilt item on the
list that stops live trading, and it was the first thing looked at. Both halves
turn out to be doors that need the owner on the other side, and one of them is
not the door the spec above names.

**The EA half cannot be committed unattended, and that is a harder rule than it
looks.** The spec says piece 1 is a new EA version plus `deploy_ea.sh` and F7 —
which reads like "the change waits for a deploy". It does not. Committing the
`.mq5` edit *is itself* the live change: the handshake greps `EA_VERSION` out of
the repo copy on every connection, so the moment the source says 1.08 and the
chart is running 1.07, on the owner's own machine and with nothing deployed:

* the top-bar EA badge goes stale (`ea_build_status`);
* **every EA Template order is refused** — `template_refusal_for_stale_ea`,
  which is bugs/033 working exactly as intended, because a template is managed
  entirely by the build on the chart;
* the macOS/Wine bridge restarts the MT5 terminal once, as soon as the book is
  empty (`ea_deploy.reload_decision`) — about two minutes managing nothing.

So an overnight commit of the EA marker would have stopped template trading on
the running demo account until someone sat down at MetaEditor. Recorded in the
broker domain README as a general rule, because it applies to every EA change,
not just this one.

**The Python half is one condition inside `record_close`**, which is golden
rule 4's frozen list. Not ours either, and the spec already says so.

**What that leaves.** Building the middle — a basket registry and a scoring
module — while both ends are unreachable would put a few hundred lines of
plumbing in the tree that nothing calls and nothing can exercise end to end.
That is the shape the 2026 audit was called for. It was not done.

**This is a one-sitting job with the owner**, and the sitting already has to
happen for the demo the spec describes: EA edit, `deploy_ea.sh`, F7, the
`record_close` condition, then open a mixed basket on demo and read
`circuit_breaker_consec_losses` before and after. Everything needed to do it is
written down above.
