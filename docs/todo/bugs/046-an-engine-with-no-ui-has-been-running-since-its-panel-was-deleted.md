# 046 — The Bounce engine has been running with no UI since its panel was deleted

**Status:** found 2026-09-12. **FIXED 2026-09-14** — option 1, on the owner's
word: *"the bounce engine has now been removed so there shouldn't be any
decisions relating to this"*. It had not been; it is now.
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

## Three reads outlived the panel

Found 2026-09-12 while attributing the event-loop stalls. `panel_data.__all__`
is the exact surface a panel calls — one named operation each. Three of Bounce's
are now referenced by nothing at all:

* **`change_signature`** — *"a cheap comparable snapshot used to decide whether
  the panel needs a re-render… it IS the diffing check."* The Reversal and
  Breakout panels clear and rebuild **six containers** on a timer and account
  for 30% of this app's event-loop stalls (`docs/todo/bugs/030`). The mechanism
  that would stop them was built, works, and is wired to a panel that no longer
  exists.
* **`param_specs`**, **`ml_features_for_signal`** — same cause, no such
  consolation.

The other two engines are clean: 17 of 17 and 13 of 13 exported names are
referenced. Pinned by `tests/refactor/test_panel_reads_have_a_panel.py`, a
shrink-only ratchet with those three listed, so the next panel removal cannot
leave its reads behind quietly.

Whether they are deleted or wired up depends on this file's own decision: they
are only dead while the panel is.

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


---

## Fixed, 2026-09-14 — and there was a third starter

The owner said the engine had been removed. It had not: it was running at the
moment he said so, having been started eight minutes earlier by an app restart.
What was removed on 2026-09-02 was the **panel**.

Reading the starters again for the fix turned up one this file had missed.
There are **three**, not two:

| | |
|---|---|
| `engines_controller.start_stopped_engines` | excludes it — correct, and always was |
| `app.py` startup | starts it unless `sg_engine_enabled` is `"0"` |
| **`app.py._signal_engine_watchdog_loop`** | **re-starts it every five minutes if it finds it stopped** |

The third is why stopping it by hand would never have held, and why a
`sg_engine_enabled = 0` in the database was not the fix either — it would work,
but it leaves the code still claiming something untrue and still starting the
engine the moment that row is touched.

**The guard is in `TestSignalEngine.start()`**, behind
`services/test_signal.PANEL_REMOVED`. One place, every path, including the
fourth caller nobody has written yet. Same lesson as bugs/014, 019 and 051:
defend the place, not each path.

It refuses out loud rather than silently — `status_detail` names the date the
panel went and this bug — because being started invisibly is how the engine
spent twelve days analysing for a screen nobody could open.

**Nothing is deleted.** The service, its database, its 173 signals and its slot
in the fixed `(breakout, bounce, reversal)` order the sync server binds by are
all intact. Reviving it is that one constant, and a test asserts the way back
actually works rather than leaving it as a claim in a comment.

Two of the three known-dead panel reads (`change_signature`, `param_specs`,
`ml_features_for_signal`) stay dead, and `tests/refactor/test_panel_reads_have_a_panel.py`
still holds them — the engine being stopped does not give them a caller.

## "Stopped" is not "deletable" — its package is now a shared library

Worth knowing before anyone reads "removed" as "delete the folder". Two live
engines import code out of `services/test_signal/`:

| importer | what it takes |
|---|---|
| `reversal_engine/re_macro.py`, `macro_backfill.py` | `market_context` — and `re_macro` feeds the **live ML gate** |
| `breakout_signal/breakout_signal_service.py` | `market_context.get_context` |
| `breakout_signal/signal_generator.py`, `breakout_signal_velocity.py` | `get_session`, `session_quality`, `session_is_active` (bugs/045) |

None of that breaks with the engine stopped — they are module-level functions,
not calls into a running engine, and the app came back clean with the Reversal
Engine's macro features intact. But it does mean the retired engine's package
is now a **shared library for the two engines that still trade**, and deleting
it would take the Reversal Engine's macro inputs with it.

Moving `market_context` and the session helpers somewhere neither engine owns
is the prerequisite for ever deleting this folder — and it is the same move
`docs/todo/bugs/057` needs for the session definitions.

---

## Deleted, 2026-09-14

Owner: *"remove the bounce engine but ensure you don't impact the market
context and anything else for the reversal engine as this is the main signal
generator ... while you can remove the bounce engine backend, don't impact the
reversal engine."*

`backend/src/services/test_signal/` and `tests/test_signal/` are gone — 18
modules and 11 test modules.

**The prerequisite named above was done first.** Everything the two live
engines imported out of that package moved to `services/market/`, which no
engine owns:

| now at | what moved | who reads it |
|---|---|---|
| `market/macro_context.py` | was `test_signal/market_context.py` | Reversal (`re_macro`, `macro_backfill`), Breakout |
| `market/news_window.py` | was `test_signal/news_filter.py` | Reversal, `market/levels` |
| `market/sessions.py` | `get_session`, `session_quality`, `session_is_active` | Breakout |
| `market/levels.py` | `compute_htf_bias`, `identify_key_levels`, `is_news_window`, the private level helpers | Breakout (service + backtest) |
| `market/indicators.py` | `compute_h4_bias`, `compute_adx`, `compute_macd_hist`, `detect_regime` | Breakout (service + backtest) |

What did **not** move is everything that read the Bounce engine's own adaptive
parameters — `check_entry_trigger`, `calculate_risk_levels`,
`check_scalp_trigger`, `calculate_scalp_risk_levels`, `_counter_bias_allowed`
and the candle-pattern helpers only those used. That was the engine, and it
went with the engine.

`tests/refactor/test_the_bounce_engine_backend_is_gone.py` holds all of it: the
package is gone, nothing imports it, each moved primitive is **called** and its
answer checked, and the Reversal Engine's macro path is exercised rather than
merely imported.

### The one thing deliberately left behind

The **name** `bounce` still occupies position 1 of 3 in
`engines_controller._ENGINE_SERVICES`, bound to `None`. `remote_node.py`
unpacks that tuple positionally into `server_start`, the sync server keys its
`signal_gen_stats` payload by the same names, and `stood_down_engines` persists
them into the database and over the wire. Dropping the slot would put the
Reversal Engine in Bounce's position on any paired node still running the old
build. The wire key stays too, carrying `{}` — which is exactly what that
snapshot already sent whenever the engine was unavailable.

Removing the slot is a coordinated two-node upgrade, not a tidy-up.

### What is genuinely lost

`panel_data.change_signature` — the cheap re-render diffing check that
`docs/todo/bugs/030` wants. It was built for the Bounce panel, orphaned when
that panel went, and has now been deleted with the rest. The Reversal and
Breakout panels still rebuild six containers on a timer. If 030 is picked up,
the mechanism is in git history, not in the tree.
