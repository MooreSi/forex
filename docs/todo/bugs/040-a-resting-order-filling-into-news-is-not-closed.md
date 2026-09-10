# 040 — A pending order that fills during a news blackout is kept

**Status:** OPEN, **not changed** — it is a design question, and the answer
belongs to the owner. Found 2026-09-09 auditing gate coverage across every
order route.
**Money:** yes — it decides whether a position opened into a news event is
kept or closed.

## The asymmetry

A genuine broker-side pending order (Limit Runner, and EA Template legs) is
accepted long before it fills. Both the **trading schedule** and the **news
blackout** are entry gates that could not be evaluated at placement time.

Only one of them is re-checked when the order actually fills:

| gate | at placement | at fill |
|---|---|---|
| Trading Schedule | not checked | **checked — and the position is immediately closed** |
| News blackout | not checked | **not checked** |

`ea_bridge/_events.py` holds three `check_trading_schedule` calls and **zero**
`check_news_blackout` calls. The schedule one is deliberate and well argued in
its own comment:

> the resting order was accepted by the broker before we could know whether
> the window's profit target would still allow it by the time it actually
> filled ... The fill already happened — an immediate real close is the only
> protective action left.

Every word of that applies to a news blackout too.

## Why it was looked for

The bias gate missed three separate order routes in one day
([080](../reversal-engine/080-no-trend-gate-on-the-telegram-path.md)), so every
route was audited against every gate. The limit-order path looked like a fourth
hole — it consults neither the schedule nor the news blackout at placement —
and **it is not**: the schedule is enforced at fill instead, on purpose. That
check is what turned up the missing half.

## The decision

Whether a resting order that fills inside a news blackout should be closed the
way a schedule-blocked one is.

**Arguments for closing it**, and it is the same argument the schedule check
already won:

* the blackout exists because price moves violently and spreads widen at those
  moments, which is precisely when a resting limit gets hit;
* the two gates sit side by side at every other entry point in the app
  (`scan_auto_execute`, `instant_entry`, `pending_activation`,
  `resolution`, `reversal_engine_live_execute` all call both);
* a trader who has switched the blackout on has said they do not want to be in
  the market then, and the position arrived without them choosing it.

**Arguments against:** closing on fill realises a spread-and-slippage loss
immediately, at the worst moment for liquidity. The schedule case accepts that
cost; a news spike is the case where it is highest.

**Not built.** It closes real positions, it is a change of intent rather than a
repair, and the cost/benefit above is genuinely two-sided.

## Related

The *cancel* half of this question — withdrawing a resting order before it fills into a blackout,
rather than closing the position after — is
[limit-orders/040](../limit-orders/040-revalidate-before-the-fill.md). This file remains the *close*
question, which is still the owner's to answer.
