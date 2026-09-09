# 032 — The "Schedule Override" banner keeps saying ON after you turn it off

**Status:** found 2026-09-09, reported live. **Display only — no trading
behaviour is affected.** Not fixed.
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
