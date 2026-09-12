# 030 — The app's own event loop stalls, and nobody has looked since July

**Status:** **Two causes fixed 2026-09-09. A THIRD found 2026-09-10** — a
full page load. See the last section.

**Superseded claim:** The high-frequency stalls were
bugs/035; the ~5s stalls were the ML fit running on the event loop, fixed on
the owner's explicit permission to touch the money path. Polling volume is
measured and left alone. See the sections at the end. Recorded 2026-09-05 so it stops being
an aside in a handoff file.
**Found:** measured as a side effect of
[bugs/013](013-ea-stalls-leave-template-trades-unmanaged.md), which ruled it
out as the cause of the EA stalls and then had no reason to pursue it.
**Touches money:** not directly, but it freezes the loop that order dispatch,
position monitoring and Telegram alerts all share.
**Severity:** unknown, which is the problem. Sub-second, frequent, unattributed.

## What is known

`backend/src/utils/loop_monitor.py` wakes every 250 ms and logs a warning when
actual elapsed time drifts more than 400 ms past expected. This app is
single-threaded cooperative asyncio, so a drift there means some coroutine
blocked synchronously and every other task on the loop — including order
dispatch — was frozen for that long.

Two independent measurements exist, both collected for bugs/013:

- **2026-08-28:** drifts of 400–770 ms roughly every 15 seconds, with about 50
  concurrent tasks on the loop.
- **2026-08-31:** 53 stalls logged over the day.

Neither was ever attributed to a coroutine.

## What is already ruled out

**It is not the EA.** Of the 53 stalls on 2026-08-31, **zero** fell within 60
seconds of any of that day's four EA-silence bursts. bugs/013 named
`[LoopMonitor]` as "the first thread to pull" and that turned out to be wrong;
the two are unrelated faults that happened to be visible in the same log.

**It is not the Telegram poll any more.** That one was found and fixed: the
bot command loop was opening a fresh `httpx.AsyncClient`, and therefore a new
TLS handshake, on every ~1 s `getUpdates` poll. Confirmed live on 2026-07-09
as thousands of `SimulationEngine._bot_command_loop ... took 0.4-1.5s`
entries, far more than any other task. `backend/src/services/telegram/bot_loop.py:149`
now holds one pooled client for the loop's lifetime. Whatever is left is
something else.

The only standing note on the remainder is
[docs/todo/refactor/HANDOFF.md:55](../refactor/HANDOFF.md) — "expect
`LoopMonitor` stall warnings — the engines are heavy at idle; not an error (a
known issue)". That is an assumption, not a measurement. "Heavy at idle" does
not explain a *synchronous block*: work spread across cooperative tasks does
not stall the loop, only work that never yields does.

## The attribution route already exists and is already on

`loop_monitor.start()` sets `loop.set_debug(True)` and
`loop.slow_callback_duration = 0.40`. That makes the stdlib `asyncio` logger
emit

```
Executing <Task ... coro=<X() running at file.py:LINE>> took Y.YYYs
```

naming the offending coroutine and its exact suspend point. Those lines flow
into the app's normal log file. **This is how the Telegram culprit was found,
and nothing has read them since.**

The watchdog's own `[LoopMonitor]` warning dumps a task-name list instead, and
the module says plainly why that is useless: it lists every task that exists
on the loop, which is nearly identical on every stall and never identifies the
blocker.

## What to do

1. **Read the slow-callback lines.** On the Windows box, over a recent day:

   ```bash
   grep "Executing <Task" logs/*.log | sed 's/.*coro=<//;s/ running at /|/;s/>.*took /|/' | sort | uniq -c | sort -rn | head -20
   ```

   That gives coroutine, source line and frequency in one pass. If one name
   dominates the way `_bot_command_loop` did, the investigation is over before
   it starts.
2. **Fix the blocking call where it is**, the way the Telegram one was fixed —
   pool the resource, or push the synchronous work to `asyncio.to_thread`.
   Do not raise `_WARN_THRESHOLD_S` to quieten the log.
3. **Then decide about asyncio debug mode.** It is currently enabled
   permanently in production (`loop_monitor.py:79`). It buys the attribution
   above and costs coroutine-origin tracking on every task. That trade is
   correct while this bug is open and worth re-examining once it is closed —
   but only with a measurement, since turning it off also removes the only
   tool that can measure it.

## Ruled out statically, 2026-09-05

A read of the obvious blocking candidates found them already handled. Recorded
so the next session does not repeat the sweep:

- **The MT5 bridge is not it.** Every call goes through
  `asyncio.wait_for(asyncio.to_thread(fn, ...))`
  (`services/broker/mt5_native.py:157`), including the 50 ms TP-ladder poll,
  which was the most promising candidate on cadence alone.
- **The self-healer's log scan is not it.** `_read_recent_log_lines` is called
  as `await asyncio.to_thread(...)` (`services/health/self_healer.py:194`).
  Note the comment block above it still describes the pre-fix state — "this
  runs unwrapped inside an async task" — which is no longer true and cost a
  few minutes here. Worth correcting when this file is next touched.
- **The cluster signal-gen stats loop is not it**, despite being the only loop
  in the app on exactly the observed ~15 s cadence
  (`_SIGNAL_GEN_STATS_INTERVAL_S = 15.0`). All three snapshot builders are
  threaded, and `_broadcast` returns immediately when no peer is connected
  (`services/cluster/sync/server.py:697`). It only serialises a payload on the
  loop when a client is actually attached, so it stays a candidate on a node
  with a live peer and nowhere else.

The conclusion is not "no cause found" — it is that a static read cannot find
this one, which is the argument for step 1 above rather than more sweeping.

## Also noticed, smaller

`recent_stalls()` and `summary()` at the bottom of `loop_monitor.py` maintain
a 200-entry ring buffer the module docstring describes as "for the Edge
Dashboard". Nothing in the repo calls either function. Either the dashboard
panel was never wired up or it was removed; the buffer has been filling for
nobody. Worth resolving in the same change — surface it, or delete it and say
so.

## Not to do

Do not treat a quieter log as progress. The warning threshold and the
slow-callback threshold are the same 400 ms by design; moving either one hides
the fault rather than fixing it, and this bug exists precisely because the
condition was labelled "known" and then left alone for two months.


---

# What they actually are (2026-09-09)

Measured across three app runs on the same day, either side of the
[035](035-a-declined-sl-adjustment-looped-forever.md) fix:

| window | duration | stalls | rate | worst | median |
|---|---|---|---|---|---|
| 14:38 - 15:58 (before 035) | 80 min | 207 | **2.59/min** | 5,099 ms | 468 ms |
| 16:33 - 18:24 (after 035) | 111 min | 53 | **0.48/min** | 4,971 ms | 480 ms |
| 18:24 - 18:50 | 25 min | 8 | **0.32/min** | 4,959 ms | 698 ms |

**There are two separate problems, and the numbers separate them cleanly.** The
rate fell more than fivefold while the worst case did not move at all.

## Cause 1 — the high-frequency stalls. FIXED.

The declined-SL-adjustment loop in [035](035-a-declined-sl-adjustment-looped-forever.md):
a message re-parsed and re-logged once a second, indefinitely, 4,099 times in
71 minutes. Fixing it took the stall rate from 2.59/min to 0.48/min. That was
not why 035 was fixed, and the size of the effect was a surprise.

## Cause 2 — the ~5 second stalls. FIXED 2026-09-09.

**The ML model fit runs synchronously on the asyncio event loop.** Caught with
the lines either side of it:

```
18:32:55,573 [ProModel] fitted n=7769 (pos=1533 neg=6236) AUC=0.820 -> ok
18:32:55,593 [RE-Engine] SIGNAL RE-9CF74A BUY congestion level=4410.14
18:32:55,594 WARNING asyncio — Executing <Task pending name='Task-687'
                                coro=<ReversalEngine._cycle_loop() ...
18:32:55,596 [LoopMonitor] event loop stalled 4959ms (expected 250ms)
```

Fitting 7,769 rows takes about five seconds, and for those five seconds
**nothing else in the app runs** — not the UI, not the EA socket reader, not
the monitor loop that manages open trades.

Two synchronous entry points, both on hot paths, in `pro_model.py`:

* `pro_likeness()` — calls `fit()` when the model is not ready, and is called
  on the **scoring path** for each candidate;
* `on_new_signal()` — calls `fit()` after every captured reference signal, by
  design ("one incremental refit per signal is the whole point of the toggle").

### Why this is not just a latency complaint

The EA reconnects when Python goes quiet. From the 15:19 log:

```
15:19:52 [EA] trade=e44091e4 ticket=1970453033 EA unhealthy -- template
         strategies have no Python fallback, leaving unmanaged until the EA
         reconnects rather than reclaiming
15:19:55 [EABridge] no data from Python in 10s — reconnecting on port 9111
```

A five-second blackout is half that budget, and it lands on a path where a
template-managed trade is explicitly left **unmanaged** while the EA is
considered unhealthy.

### The fix

The owner gave explicit permission to touch the money path
(*"you can also fix money path issues"*), so both halves were done.

`fit_in_background()` submits to a single-worker pool and returns at once.
`on_new_signal` uses it, and `pro_likeness` uses it **instead of** blocking,
returning `NEUTRAL` — already its documented answer for "not trustworthy yet",
and already what it returns whenever scoring raises.

**The behaviour change, stated plainly:** signals arriving before the first
successful fit now score `NEUTRAL` rather than waiting for a model to train.
On the first signals after a restart, the ML gate sees a neutral pro-likeness
where it used to see a real one five seconds later.

**One worker, and an in-flight guard.** Signals arrive faster than a fit
finishes. Without the guard, eight signals enqueue eight full trains back to
back on unchanged data — and that is not the same failure as concurrency,
which is what the first version of the test wrongly asserted against. Pinned by
`tests/reversal_engine/test_pro_model_fit_does_not_block_the_loop.py`.

**Not changed:** the explicit "fit now" button in the Reversal panel still runs
inline. It is a rare, user-initiated action where a wait is expected — but it
does freeze the loop for the same five seconds, and is worth revisiting.


---

# Two more measurements (2026-09-09, same session)

## No other rescan loops remain

The [035](035-a-declined-sl-adjustment-looped-forever.md) and
[015](015-bare-direction-message-is-rescanned-forever.md) defects were the same
shape: something not marked as handled, re-processed every cycle. The obvious
question is whether there are others.

Normalising every log line (timestamps and numbers stripped) over a 58-minute
run: **no message repeats more than 20 times.** Those two were the only ones.
Worth re-running after any change to the scan path; it takes seconds and it is
how both were found.

## Bridge polling volume — 327 calls a minute with nothing open

Same 58-minute window, **zero open positions** for most of it:

| endpoint | rate |
|---|---|
| `/positions` | 91.5/min |
| `/candles/XAUUSD` (four series) | 59.3/min |
| `/tick/XAUUSD` | 56.2/min |
| `/account` | 47.6/min |
| `/history` | 32.0/min |
| `/health` | 31.9/min |

That is **5.5 HTTP round trips per second**, every one of them crossing into
the Wine-hosted MT5 bridge. The history calls are the striking ones:

| query | rate |
|---|---|
| `/history?days=90` | 16.8/min — every 3.6 seconds |
| `/history?days=365` | 4.3/min — a full year of deal history, four times a minute |
| `/history?days=43`, `days=7` | 4.3/min each |

## How the stalls break down against that

Eleven stalls in the window: ten between 424 ms and 1,083 ms, and the single
4,959 ms ML fit. The sub-second ones cluster at startup and are preceded by a
mix of `/candles`, `/positions`, `/history` and `/account` — no single culprit,
which is consistent with the loop simply being busy rather than one call
blocking.

**So the ranking is:** the 035 loop (fixed, five-sixths of the rate), the ML
fit (identified, all of the worst case), and general polling volume
(measured, not yet a proven cause of anything).

**The polling is NOT being changed here.** Lowering a poll interval changes how
quickly the app notices a fill or a close, which is money behaviour and the
owner's call. It is recorded because 4 requests a minute for a year of deal
history, with nothing open, is unlikely to be deliberate.


---

# Cause 3 — opening the page (2026-09-10)

The fix above removed the ML fit, and the multi-second stalls stopped for four
hours. Then, at 06:36:

```
06:36:31 [LoopMonitor] event loop stalled 2065ms
06:36:33 [LoopMonitor] event loop stalled 1548ms
```

**So "the multi-second class is gone" was too strong a claim, and this
corrects it.** The ML fit was one cause of multi-second stalls, not the only
one.

## What it is

The 2,065 ms stall's task list carries about twenty-five render tasks that the
sub-second stalls around it do not:

```
_render_active_trades.refresh, _render_calendar.reload,
_render_connected._refresh_pending, _render_connected._update_slot_status,
_render_equity_curve.refresh_chart, _render_history, _render_ml,
_render_pending_signals.refresh, _render_slot_feed.refresh,
_render_tg_signals.refresh, _render_trade_table.refresh_table,
attach.open_start_here, render._refresh_all, render._refresh_candles,
render._refresh_fvgs, render._render_analytics, render._render_balance,
render._render_stats, render.refresh_perf ...
```

`attach.open_start_here` is a fresh client attaching. Every panel refreshes at
once, each doing its own database reads and bridge calls, all on the event
loop. Nothing was scheduled at 06:36 and no engine cycle lines them up — a
browser opened the page.

## Why it is worth recording rather than shrugging at

* It happens **exactly when someone is watching**, which is also when they are
  most likely to be about to act on what they see.
* The EA reconnects after ten seconds of Python silence and a template trade
  has no Python fallback while that lasts (see
  [013](013-ea-stalls-leave-template-trades-unmanaged.md)). Two seconds is a
  fifth of that budget, spent on rendering.
* It scales with the number of clients. The Mac connects to this app too.

## Not fixed

The shape of the fix is the same as the ML one — do the work off the loop, or
stagger the panels so they do not all refresh in the same tick — but it is a
frontend change across roughly a dozen render functions, and it is a latency
problem rather than a money one. Recorded with the evidence so the next person
does not have to find it again.

**Rate check for the record**: between 03:30 and 06:35, with the ML fit off the
loop and nobody looking at the page, there were **no stalls at all**.


---

# Cause 3, measured properly (2026-09-10 07:43)

"About twenty-five renders in one tick" was inferred from a task list. Measured
instead, by loading the page and counting every bridge call in the 25 seconds
that followed:

| endpoint | calls | |
|---|---|---|
| `/positions` | **89** | **with zero positions open** |
| `/account` | 80 | |
| `/tick/XAUUSD` | 61 | |
| `/health` | 52 | |
| `/history?days=90` | 30 | |
| `/history?days=365` | **9** | a full year of deal history, nine times |
| `/history?days=44`, `days=7` | 9 each | |
| **total** | **388** | **15.5 a second** |

Steady state with nobody on the page is 327 a MINUTE. A page load is roughly
**three times that rate**, sustained for half a minute, and every one of those
crosses into the Wine-hosted MT5 bridge.

**89 reads of `/positions` when nothing is open** is the clearest sign that
panels are not sharing: each asks the bridge for itself, repeatedly, rather
than one read being fanned out.

## The fix, and why it is not applied here

Coalescing: a short TTL in front of the bridge's read methods, so N panels
asking for `/positions` within the same tick get one round trip.

**It must not be applied to the trading path.** `monitor_cycle` reads positions
to manage open trades, and serving that from even a one-second cache would mean
acting on a stale book. So the cache has to be scoped to UI reads only, and
drawing that line wrong is a money bug rather than a latency one — which is why
it is written down rather than done unattended.

A cheaper first step with none of that risk: find out why nine separate callers
each want a year of deal history on every page load. That looks unintended
rather than merely uncoalesced.

---

# Cause 3: one caller attributed (2026-09-10, night)

The "cheaper first step" above — *find out why several callers each want a year
of deal history on every page load* — is now partly answered, by reading the
code rather than by instrumenting the bridge.

**The three History panels are already coalesced.** `_equity_curve` (365 days),
`_trade_table` and `_calendar` (whatever the user selected) all go through
`frontend/pages/history/_deal_cache.cached_deal_history`, 60-second TTL, keyed
by `days`. That was the fix landed earlier the same day, and it holds: there is
no remaining direct `get_deal_history` call anywhere under `frontend/pages/`.

**The one left is the header, and it is a duplicate implementation, not merely
an uncoalesced read.** `frontend/app/_header.py:554` asks the bridge for
**3,650 days** of deal history — the whole account life, the largest payload
the app ever pulls — to work out net deposits for the header's lifetime-P&L
figure. Its cache (`_net_deposited`, `_deposit_fetch_at`) is built **inside
`build_header`**, so it is per client and per page build: every browser that
opens the page pays for that fetch, and pays again every 5 minutes it stays
open.

The same number already exists, computed once and shared:

| | header, inline | `services/broker/deposits.get_total_deposits` |
|---|---|---|
| Cache | in-memory, per client, 5 min | `app_config`, per install, 1 hour |
| Survives a page reload | no | yes |
| Counts | `type == 2` deals, credits minus debits | every deal with no `position_id` |
| Gives up when | `credits == 0` (keeps the last value) | never; returns 0.0 on error |
| Reached from | nowhere else | `runtime.get_total_deposits`, used by `frontend/pages/trading/__init__.py:69` |

So the Trading page and the header can already disagree about the same
account's net funding, and the header is the narrower of the two: MT5 balance
operations that are not `DEAL_TYPE_BALANCE` (credit, correction, bonus) are
counted by the service and missed by the header.

## Why it was not changed tonight

Routing the header through `engine.get_total_deposits()` is three lines, kills
the 3,650-day fetch, and makes two panels agree. But the two filters are not
equivalent, so it **changes a money figure the owner reads on every screen** —
the header's lifetime P&L — by an amount that cannot be determined from here:
it depends on deal types in the MT5 account, which is not in the database and
cannot be read without the broker.

It also cannot be pinned by a test as things stand. `_refresh_header` is nested
inside `build_header` and is not callable from a test — `test_main_page_renders`
says so in its own docstring — so the only available check would be a
source-text grep, which passes just as happily with the code deleted.

**What it needs:** the owner looking at the header before and after, or
`_refresh_header` lifted to a callable function first so the change can be
tested. Either is a session with someone watching, not an overnight edit.

## The test blocker is gone (2026-09-12)

> *"or `_refresh_header` lifted to a callable function first so the change can
> be tested"* — the second of the two routes above.

The part that needed lifting was never the whole of `_refresh_header`; it was
the eight lines inside it that decide what counts as funding. Those are now
`frontend/app/_header_pnl.net_deposited_from_deals`, pinned by
`tests/frontend/test_header_net_deposited.py` (six cases, four mutants killed:
`credits - debits` → `+`, `credits <= 0` → `< 0`, the `type == 2` filter
removed, and the withdrawal branch inverted).

**The number did not change.** Same filter, same "no credit in the window means
no answer" rule, same caller and same cache. What changed is that the header's
definition of funding is now readable, comparable to the service's, and fails a
test if anyone alters it by accident.

The last test in that file states the difference between the two
implementations as an executable assertion: a balance operation that is not
`DEAL_TYPE_BALANCE` is counted by `get_total_deposits` and invisible here.

**Still the owner's, and unchanged:** routing the header through
`engine.get_total_deposits()` — which is what actually kills the 3,650-day
fetch this section was written about. It moves a money figure he reads on every
screen, by an amount that depends on deal types at the broker. The three-line
change is now safe to make and safe to test; it is not safe to make unattended.
