# 013 — The EA stalls, and template trades have no fallback while it does

**Status:** observed on the demo account 2026-08-28. **Steps 1 and 2 answered
2026-09-01 from 30 days of rotated logs — and step 1's earlier conclusion is
SUPERSEDED. Step 3 still needs the owner; the options are now written out.**
**Found:** during the M1 harvest demo (docs/simon-handover/session-agenda.md, Part B2)
**Touches money:** yes — an unmanaged live position
**Severity:** intermittent, silent, and the app already knows it is happening

## What was seen

While demonstrating the harvest fix, an EA-managed position went unmanaged for
roughly eight seconds:

```
15:56:29 → 15:56:36   [EA] trade=5b1990d4 ticket=1883083490
                      strategy=template:Harvest $30
                      EA unhealthy -- template strategies have no Python fallback
15:56:37              position closed, +$54.40
```

No disconnect and no reconnect in that window — the EA simply stopped
heartbeating, then resumed. The harvest threshold was $30. Profit passed $30
during the stall and reached $54.40; the moment the EA resumed it harvested
immediately and correctly.

So the harvest logic is fine. What is not fine is that for those eight seconds
**nothing was managing a live position**: no harvest, no breakeven, no
trailing, no partial ladder. This time the price happened to move favourably.

## Why it matters more than it looks

The warning says it outright: *template strategies have no Python fallback*.
Every other strategy degrades to Python management when the EA is unavailable.
Template strategies do not — they are managed entirely inside MT5, so an EA
stall is a total management outage for those trades, for as long as it lasts.

A stall through a reversal costs the difference between the harvest level and
wherever price is when the EA wakes up.

## What is already known

- The app detects it. `monitor_loop` logs the warning once per second per
  affected trade, so the data to measure frequency is already in the log.
- The app's own event loop was stalling in the same period — 400–770 ms every
  ~15 s, with roughly 50 concurrent tasks (`[LoopMonitor] event loop stalled`).
  Whether the two share a cause is unknown and worth establishing first.
- The EA had also been running a **stale build** (compiled 2026-08-21 against
  source last modified 2026-08-27). Recompiling changed the template payload it
  accepted from 65 fields to 102, so the stale build was materially different.
  The stall was observed on the stale build; it has not yet been seen on the
  recompiled one.

## What to do

1. **Establish whether it still happens on the current build.** Grep the log
   for `EA unhealthy` over a full session now that 2026-08-28 16:05's build is
   running. If it has stopped, this may have been the stale build and nothing
   more.
2. If it persists, find out which side stalls — the EA inside MT5, or the
   bridge/socket between them. The `[LoopMonitor]` correlation is the first
   thread to pull.
3. Separately, decide whether "no Python fallback for template strategies" is
   acceptable. It is a deliberate design (MT5 owns those trades), but it means
   EA availability is a single point of failure for them, with no alarm beyond
   a log line.

## Not to do

Do not add a Python fallback that manages template trades while the EA is
merely *believed* unavailable. Two managers acting on one position is worse
than none, and the health signal is a heartbeat timeout — exactly the thing
that is unreliable when the system is stressed.

---

## Step 1 result, 2026-08-28 evening

**It has not recurred on the recompiled build.** 76 `EA unhealthy` warnings
today, and the last one is at **16:05:24** — the same minute the recompiled EA
went in. Nothing in the 3.7 hours after that, with the app running throughout.

That is consistent with the stale build being the cause, but it is 3.7 hours on
one evening, not proof. The distribution by hour is worth keeping:

```
02:00   1
07:00  12
15:00  60      <- the M1 harvest demo window
16:00   3      <- all at 16:05:xx, the tail of the last stall
```

**Two of the 76 are a different problem, and one of them is most of the count.**
The warnings name three trades:

```
40   trade=83aa3510  ticket=0           template:Asian Reversal - ATR
30   trade=5b1990d4  ticket=1883083490  template:Harvest $30
 6   trade=8fbabe87  ticket=1878717014  template:GD
```

`83aa3510` has **ticket 0 and does not exist at the broker** — it is a phantom
placeholder row that has been `open` since 2026-08-27, and it is now
[bugs/016](016-phantom-open-trade-consumes-a-trade-slot.md). It also holds one
of the five trade slots.

So **more than half of this bug's evidence was a trade that was never live**.
The real unmanaged-position exposure is the 36 warnings against `5b1990d4` and
`8fbabe87`, both of which had genuine tickets. The eight-second stall during the
M1 demo is still real and still the thing worth understanding.

**What is left:** step 2 (which side stalls) only matters if it recurs — worth
re-checking after a longer session on the current build. Step 3 (whether "no
Python fallback for template strategies" is acceptable) is unchanged and still
needs your decision, and 016 does not affect it either way.

---

## Steps 1 and 2, answered from the logs, 2026-09-01

The app keeps 30 daily rotated logs. That is enough to answer both questions
without waiting for another session.

### Step 1: it DID recur on the recompiled build

The 2026-08-28 conclusion — "not recurred, consistent with the stale build
being the cause" — was true on the evening it was written and is no longer
true. Counting only warnings against a **real ticket** (a live position;
`ticket=0` rows are bugs/016 phantoms and were more than half the original
evidence):

| day | real-ticket warnings | distinct live tickets | bursts |
|---|---|---|---|
| 2026-08-27 | 30 | 4 | 3 |
| 2026-08-28 | 36 | 2 | 2 (last at 15:56, before the 16:05 recompile) |
| 2026-08-29 | 0 | 0 | 0 |
| 2026-08-30 | 0 | 0 | 0 |
| **2026-08-31** | **29** | **5** | **4** |
| 2026-09-01 | 1 | 1 | 1 (the owner removing the EA by hand, during the demo) |

**Four bursts on 2026-08-31, three days after the recompile, against five
distinct live tickets.** The stale build was not the cause, or not the only
one.

Each burst, with the length of the unmanaged window:

```
08:00:35 -> 08:00:41   6s   two trades at once
13:01:43 -> 13:01:46   3s
14:43:19               0s   a single warning
15:24:22 -> 15:24:31   9s
```

Short — 0 to 9 seconds, about four times in a trading day.

### Step 2: the event-loop correlation is dead

The bug named `[LoopMonitor] event loop stalled` as "the first thread to
pull". It is not the thread.

**Of the 53 event-loop stalls logged that day, ZERO fell within 60 seconds of
any of the four bursts.** The app's own loop stalling and the EA going quiet
are unrelated. Whatever is happening is on the MT5 or socket side.

### What "EA unhealthy" actually means, which changes the risk

```python
_HEARTBEAT_TIMEOUT_S = 8.0        # ea_bridge/__init__.py
if(GetTickCount64() - g_lastPingSent >= 2000)   # ForexTraderBridge.mq5:652
```

The EA pings every 2 seconds; the app declares it unhealthy after 8. So the
warning means **four missed pings**, and it says the app has not HEARD from the
EA — not that the EA has stopped managing the trade. Those are different
claims and the app cannot tell them apart from its side.

One of them is confirmed genuine: during the 2026-08-28 M1 demo, profit passed
the $30 harvest threshold *during* the stall and was not taken until the EA
resumed. That EA really was not executing.

### And the part that shrinks the exposure

**Every order path puts the stop loss at the broker.** Market entries
(`ForexTraderBridge.mq5:1105`), resting limit orders (`:1242`) and grid anchors
(`:1631`) all pass `sl` to `trade.Buy`/`BuyLimit`. So a stalled EA does **not**
leave an unprotected position: MT5 still closes it at the stop.

What is lost during a stall is the *discretionary* half — harvest, breakeven
moves, trailing, the partial ladder. And one concrete loss case: **grid anchors
are placed with `sl` but TP `0.0`** (`:1631`), so their take-profit exists only
inside the EA. A stall that spans the TP misses it entirely.

So the honest severity is **missed profit-taking and un-trailed stops for a few
seconds, a few times a day** — not an unbounded loss.

---

## Step 3 — the decision, with options

The constraint from the top of this file stands: **do not have Python manage a
template trade while the EA is merely believed unavailable.** Two managers on
one position is worse than none, and the health signal is exactly the thing
that is unreliable when the system is stressed.

### A — alarm, do not act

Keep the no-fallback design. Add a real alert (Telegram) when a template trade
is unmanaged past some threshold, instead of a log line nobody is watching.

*Costs nothing, risks nothing, reduces no exposure.* It converts a silent
condition into a visible one. Given the windows are 0-9s, most alerts would
arrive after the stall had already ended.

### B — make the signal trustworthy before anything acts on it

Today the app infers EA health from silence. Have the EA report what it has
actually done — a last-managed timestamp per trade, or a heartbeat that says
"still managing N trades" — so the app can tell **"EA silent"** from **"EA not
working"**.

*This is the prerequisite for C, and it is worth doing on its own.* It also
tells us what the four daily bursts really are: if the EA reports it was
managing throughout, they are missed pings and there is no exposure at all.

### C — let the broker be the fallback, not Python

Narrow and specific: grid anchors go to the broker with no TP. Push their TP to
the broker as well, so a stall that spans the take-profit closes at the broker
instead of missing it.

*No second manager, no dual control — the broker already holds the stop, this
just gives it the target too.* But it changes what is sent on an order path and
would need a demo session before shipping.

The catch: it only helps where the EA's intended exit is a fixed price. It does
nothing for harvest, trailing or a partial ladder, which are decisions rather
than levels.

### D — accept it

Four short stalls a day, the stop always at the broker, cost is opportunity
rather than loss. Record the measurement, re-check in a month.

*Defensible on the current evidence, and the evidence is now real rather than
anecdotal.*

### What I would do

**B, then decide again.** Acting on a signal the file itself calls unreliable
is what the "Not to do" section warns against, and B is the only option that
answers whether there is any exposure to reduce. It is also cheap and touches
no order path.

If B shows the EA really does stop working, **C** for the grid-TP case and
**A** for everything else.

If B shows the EA keeps managing through the silence, this bug is a logging
problem and the answer is **D** plus the throttle that already landed.
