# 046 — The Bounce engine has been running with no UI since its panel was deleted

**Status:** found 2026-09-12, confirmed against the live install while it was
happening. **Not fixed** — the one-line fix stops an engine, and whether this
one should keep collecting research data is the owner's call, not an
overnight one.
**Touches money:** not today, and only because of a second switch. `sg_live_execution`
is **0** on this install, so the engine cannot place an order. If it were 1
it would be placing live MT5 orders with nothing on screen saying so.
**Severity:** the invariant the code says it enforces is not enforced.

## What the code says

`frontend/pages/test_panel/__init__.py`, written when the owner had the panel
removed on 2026-09-02:

> *"The bounce SERVICE still exists … but it is excluded from
> `start_stopped_engines()`, **so it cannot run with no panel to show that it
> is running**."*

`tests/frontend/test_bounce_generator_removed.py` makes the same argument at
more length, and it is a good one:

> *"Removing the tab alone would have been the dangerous half of the job …
> a Bounce engine with no panel would still be startable, and it places live
> MT5 orders when running. An engine that can trade with nothing on screen
> showing that it is trading is strictly worse than one you can see."*

## What is actually happening

The engine is running right now. Read from the live `test_signal.db` at
**2026-09-12 06:58 UTC**, on a Saturday:

```
2026-09-12T06:57:29   ''   Market closed — weekend
2026-09-12T06:56:29   ''   Market closed — weekend
2026-09-12T06:55:29   ''   Market closed — weekend
```

One analysis row a minute, continuously, for the ten days since its panel was
deleted. It is fetching M5, M15, H1 and H4 candles from the bridge on every one
of those cycles.

## Why the guard misses

`start_stopped_engines()` is the **power / mode toggle's** path, and the
exclusion there is correct. App startup is a different path and does not use
it — `backend/src/app.py`:

```python
if _tdb.get_config("sg_engine_enabled", "1") != "0":
    te.start()
    log.info("[startup] Signal engine auto-started")
```

Default `"1"`. So every launch of the app starts it, and the preference key
that would stop it (`sg_engine_enabled`) is only ever written by a **Stop
Engine** button that no longer exists on any screen. There is no way to turn it
off from the UI, because the UI is gone.

Two paths to one place, one of them defended — the same shape as bugs/014 and
bugs/019.

## Why it was not fixed here

The fix is to make app startup honour `_NOT_BULK_STARTED` as well, which is
three lines. But it stops an engine that:

* is still learning and still writing its own ledger;
* is still mirrored to the VPS through the sync server, which is handed the
  instance at startup (`bounce_engine=te`); and
* the owner may deliberately want kept running for research, having only asked
  for the *panel* to go.

Stopping it unattended could quietly end a data series he wants. Leaving it
continues a state that has held for ten days and has placed zero orders. So
this is filed rather than done — and it is filed loudly, because the code
currently claims a safety property it does not have.

## Two things that WERE done

* The claims above are corrected in place, so nobody reads the old ones as
  fact. The bulk-start exclusion is real and is still tested; what is corrected
  is the sentence saying the engine therefore cannot run.
* The engine now says, in its own log, when it has stopped producing —
  `docs/simon-handover/034`. That does not make it visible, but it means the
  next fortnight of silence is not invisible too.

## The decision

1. **Stop it** — app startup honours the same exclusion. Matches what the code
   already claims and what removing the panel implied.
2. **Keep it, and say so** — leave startup alone, correct the comments to say
   it runs headless on purpose, and accept that it can only be stopped by
   editing `sg_engine_enabled` in the database.
3. **Give it a panel back** — the safest of the three if the data is wanted:
   an engine that is running should be visible.

`sg_live_execution` must stay **0** under options 2 and 3. An engine that can
place orders with no screen is the thing the original change existed to
prevent.
