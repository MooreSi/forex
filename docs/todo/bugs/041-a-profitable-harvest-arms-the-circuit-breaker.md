# 041 — A profitable Global Harvest pushes the circuit breaker toward a halt

**Status:** **ANSWERED 2026-09-11 — option 1**, owner: *"a harvest shouldn't
trip or count towards the breaker."* **NOT BUILT**, and it cannot be built
entirely on this side — see *What option 1 needs* at the bottom. One
consequence of it is worth a yes/no before anyone writes the code.
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

**ANSWER (invisible both ways, or reset on a winning basket?):**
