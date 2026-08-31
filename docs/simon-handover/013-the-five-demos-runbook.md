# The five demos — a runbook for one sitting

**For:** Simon, at an MT5 terminal on the **demo** account
**Time:** about 40 minutes for all five
**Status of the code:** all five fixes are written, tested and mutation-tested.
None of them is `done`, and none becomes `done` because a test is green. Each
needs the run below, on a terminal, with your eyes on it.

## Why you are doing this rather than an agent

Golden rule 1 says no real or demo order is ever placed by the app's own
sessions, to test or otherwise. That rule is why this file exists instead of a
transcript of someone having already done it.

What has been done instead: every one of these five scenarios is driven
end-to-end offline against the fake broker, in
[`tests/e2e/test_killer_demos.py`](../../tests/e2e/test_killer_demos.py). Each
has a negative control, and each was verified by re-introducing the original
bug and watching the test go red — eleven mutations, all caught. That proves
the code paths join up. It does not prove the EA behaves as expected, that MT5
returns the retcodes we assume, or that the timings hold on a real socket.
**Those three things are what your sitting is for.**

---

## Before you start

1. Demo account only. Check the account number in the terminal title bar.
2. Set the position size to the broker minimum.
3. Have the app's log open — most of what you are checking is a log line.
4. **Fix the settings first.** Your demo account currently has the risk
   governor OFF and max daily loss at 20%, not the 3% you confirmed. See
   [011](011-your-halt-settings-do-not-match-what-you-confirmed.md). Demo 5
   will not do anything meaningful until this is corrected.

---

## Demo 1 — a slow EA must not cause a second order (stage3/010)

**The failure it prevents:** on 2026-07-30 five signals became roughly 133
opens and 36 live positions the app could not see.

1. Send a signal to a channel the app auto-executes.
2. The moment it arrives, **pause the EA** in the terminal (remove it from the
   chart, or turn AutoTrading off) so its acknowledgement cannot get back in
   time.
3. Wait for the ack timeout (5s, or 10s + 5s per leg for a template).

**Expect:** exactly **one** position on the account. The log says
`[dedup] adopted existing broker order ... instead of sending a duplicate`.

**If you see two positions, stop.** That is the original bug and nothing below
should be run until it is understood.

---

## Demo 2 — a lost answer is not a "no" (stage3/020)

**The failure it prevents:** a signal whose send got no answer being handed
straight back to the scheduler, which retries it every 20 seconds.

1. Send a signal with the EA paused, **and** pull the bridge connection
   (close the bridge program) before the fallback can ask the broker anything.

**Expect:** the signal shows as **`unknown`**, not `pending`. The log says
`send outcome UNKNOWN ... parking, NOT retrying`. No order is re-sent. Leave it
five minutes and confirm nothing else happens.

> **Read this one carefully.** Driving this demo offline on 2026-08-31 found
> that the fix did not reach this path at all: the fresh-Telegram-signal route
> opens the trade directly and never went through the routing 020 added, so an
> unanswered send was reset to `pending` — the exact dangerous state. Two
> further guards were missing underneath it. All three are now fixed and
> pinned, but **this demo is the one most worth watching closely**, because it
> is the one where the code was most recently wrong.

---

## Demo 3 — the position nobody has a row for (stage3/030)

1. Send a signal and **kill the app** (close the window) between the order
   reaching MT5 and the row reaching the database. A second or two after the
   fill is about right; repeat if you miss the window.
2. Restart the app and wait for a reconciliation pass (every 12 monitor
   cycles).

**Expect:** the log names the position as ours, once —
`we placed this and then lost its row — nothing is managing it`. It is **not**
closed, adopted or written to the database.

**The repairers are not built on purpose.** They would write, and they would
route through the frozen close path. This pass reports; you decide.

---

## Demo 4 — a refused close must not become a database close (stage3/040)

**The failure it prevents:** the app booking a profit that never happened and
then no longer managing a position that is still live and still moving.

1. Open a trade and set the profit-close target low enough that the next tick
   trips it.
2. **Turn AutoTrading off** in the terminal so MT5 refuses the close.

**Expect:** the trade stays **open** in the app and in MT5. A Telegram alert
arrives saying the close was refused. **Nothing** appears in history and no
P&L is booked.

Then turn AutoTrading back on and confirm the next attempt closes normally —
that half matters just as much.

---

## Demo 5 — the breaker actually stops trading (stage3/050)

1. Set the daily loss limit to a number one losing demo trade will breach.
2. Let a trade close at its stop.
3. Send another signal.

**Expect:** the second signal is **recorded but not traded**. The app shows the
halt reason, and the reason names the number that tripped it.

---

## When you are done

For each demo, write **pass** or **what actually happened** in
[`docs/todo/refactor/stage3/PROGRESS.md`](../todo/refactor/stage3/PROGRESS.md),
next to its row. A demo that was not run is not a pass, and a task with no
recorded demo is not `done`. That distinction is the whole point of the file.

Three things are still open regardless of how these go, and they are yours to
decide, not anyone else's:

- [011](011-your-halt-settings-do-not-match-what-you-confirmed.md) — your halt
  settings do not match what you confirmed
- [012](012-should-a-resting-order-use-a-trade-slot.md) — should a resting
  order consume a trade slot
- 030's repairers — report-only today; making them act is a decision about
  money moving without you watching
