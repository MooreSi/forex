# 041 — A profitable Global Harvest pushes the circuit breaker toward a halt

**Status:** OPEN, **not changed** — how a basket should score against the
breaker is a design decision, not a repair.
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
