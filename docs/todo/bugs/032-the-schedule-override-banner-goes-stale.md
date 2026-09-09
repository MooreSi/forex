# 032 — The "Schedule Override" banner keeps saying ON after you turn it off

**Status:** found and **FIXED 2026-09-09**. **Display only — no trading
behaviour was affected.**
**Money:** no. The banner is informational; the gate itself reads the flag
fresh on every signal.

## What was seen

The owner turned the Trading Schedule off and Trading > Strategy carried on
showing the amber **Schedule Override** banner.

## It is stale, not wrong

Verified against the live database at the time of the report:

```
is_trading_schedule_enabled() -> False
app_config['trading_schedule_enabled'] -> '0'
```

Both demo databases agree. `get_app_config` is not cached, so there is no
stale read — the flag really is off.

`frontend/pages/trading/_strategy_cards.py:77` evaluates it **once, while the
page renders**, and the row is drawn or not drawn there and then. Its own
comment says so: *"this renders once on page load"*. Changing the setting on
another tab therefore leaves the already-rendered banner in place until the
page is reloaded.

**A browser refresh clears it.**

## Why it is still worth fixing

The banner exists to explain why a schedule window may be overriding the
strategy picked below it. A stale one says the opposite of the truth, and it
is exactly the sort of screen an operator checks *before* deciding whether a
trade was routed as expected.

The card is rebuilt on the page's refresh cycle elsewhere; this row sits
outside it. Either move it inside, or bind the label to the flag.

## Not to be confused with

`docs/simon-handover/017` (which clock the schedule runs in) and
`reversal-engine/031`'s database switch — the flag was checked in **both**
demo databases and is off in both, so the account move did not cause this.


---

## Fixed, 2026-09-09

The banner row is now built unconditionally and its **visibility** follows the
flag, rather than the row being created only when the schedule is on — with
nothing there to turn back on, a refresh could never restore it.

It rides the card's **existing** 60-second poll (`ui.timer(60,
_refresh_tooltips_from_db)`) instead of adding a second timer, so the cost is
one extra flag read a minute.

A reader that throws leaves the banner showing whatever it last showed:
this runs on a UI timer, and a database hiccup must neither raise into the
timer nor blank a safety-relevant banner.

Six tests, red first, four mutants killed — the refresh doing nothing (the
original bug), initial visibility ignoring the flag, a throwing reader blanking
the banner, and the row never being registered so the refresh cannot see it.

Rendered under an explicit `Client` in the tests rather than the ambient slot,
for the reason in the frontend domain file: the shared render harness tears the
default slot stack down when it finishes, so a detached render passes alone and
fails once any harness test has run first.
