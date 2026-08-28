# 013 — The EA stalls, and template trades have no fallback while it does

**Status:** observed on the demo account 2026-08-28, not fixed
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
