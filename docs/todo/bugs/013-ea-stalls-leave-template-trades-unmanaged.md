# 013 — The EA stalls, and template trades have no fallback while it does

**Status:** observed on the demo account 2026-08-28. **Step 1 done the same
evening — see the findings at the bottom. Not fixed; step 3 still needs the owner.**
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
