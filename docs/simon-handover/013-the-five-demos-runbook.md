# The five demos — a runbook for one sitting

**For:** Simon, at an MT5 terminal on the **demo** account
**Time:** about 40 minutes for all five
**Status of the code:** all five fixes are written, tested and mutation-tested.
None of them is `done`, and none becomes `done` because a test is green. Each
needs the run below, on a terminal, with your eyes on it.
**Last checked against the code: 2026-09-01.** Every log line quoted below was
confirmed to still exist and to still be spelled that way, and the offline
demos were re-run (`tests/e2e/test_killer_demos.py`, 15 passed). Five things
had drifted since this was written; each correction is marked **[2026-09-01]**.

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
4. **Set your halt settings** — governor on, daily loss 3%, drawdown 10%. See
   [011](011-your-halt-settings-do-not-match-what-you-confirmed.md).

   **[2026-09-01] Two corrections to what this step used to say.**

   It said the code defaults max daily loss to 20%. **That was fixed** — the
   schema default and `governor.py`'s fallback are both 3.0 now, and a test
   pins all three sources agreeing. What is still unknown is **the value
   stored on your account**, which nobody but you can see. Check it in the UI
   rather than assuming either number.

   It also said demo 5 would not do anything meaningful until the governor was
   switched on. **That is not true.** `apply_daily_loss_halt_on_close` runs
   *regardless* of `risk_governor_enabled` — deliberately, because a loss
   ceiling has nothing to do with the governor's sizing model. Demo 5 tests the
   daily-loss halt and will fire with the governor off. Turn it on anyway,
   because you want it on; just do not read a passing demo 5 as evidence that
   the governor itself is working.

---

## Demo 1 — a slow EA must not cause a second order (stage3/010)

**The failure it prevents:** on 2026-07-30 five signals became roughly 133
opens and 36 live positions the app could not see.

1. Send a signal to a channel the app auto-executes — **or place a Market
   Order from the Trading page**, which is better: it removes the channel, the
   parser and the scan loop as variables and leaves only the code under test.

   **[2026-09-01] The strategy matters, and it is not optional.** Use a
   non-template EA-portable strategy — `trail_stop`, `scale_out`,
   `adaptive_runner`, `be_runner`, `conservative`, `conservative_trial`,
   `fixed_rr`, `limit_runner`, `no_sl_scale`, `orb_fixed`, `protected_scale`,
   `reversal_runner`, `scalp_runner`, `signal_climber`. **Anything starting
   `template:` takes a different branch entirely**: an EA-template ack timeout
   records a placeholder row and never falls back, so no dedup line is ever
   printed and the demo cannot pass. That is not a failure — it is the other
   half of the same fix, and it is what produced the two placeholder rows on
   the owner's account overnight on 2026-09-01.
2. The moment it arrives, **remove the EA from the chart** — right-click the
   chart, Expert Advisors, Remove. The smiley in the top-right corner
   disappears when it is gone. Rehearse the click path before you start: the
   window is 5 seconds.

   **[2026-09-01] It must be Remove, NOT AutoTrading off.** This step used to
   offer them as equivalent. They are not, and the difference decides whether
   the demo tests anything.

   The EA places the order and acks afterwards
   (`mql5/ForexTraderBridge.mq5:1104` then `:1212`), so there is a real window
   where the broker holds an order stamped `ea:<trade id>` and the app has not
   heard back. Removing the EA lands in that window, and the dedup guard finds
   that stamp and adopts the order instead of sending a second.

   With AutoTrading off, `trade.Buy` fails outright, the EA immediately sends
   `trade_open_failed`, and the app gets a clean **rejection** rather than a
   timeout. It falls back to the Python bridge, places one order, prints no
   dedup line — and you have tested nothing while everything looks correct.

   (AutoTrading off IS the right tool for demo 4, where the point is to make
   MT5 refuse a close.)
3. Wait for the ack timeout. **[2026-09-01]** A non-template strategy — which
   is what this demo needs — is a flat **5 seconds**. Templates are
   `10s + 5s per leg`, capped at 60s, which is why the owner's overnight
   placeholders timed out at 15s (one leg). Verified at
   `services/trading/open_trade.py:581-585`.

**Three outcomes, and only one is a pass:**

- `[dedup] adopted existing broker order ... instead of sending a duplicate`
  — **pass**. One position on the account.
- One position, no dedup line, and `[EA] handoff failed ... falling back to
  Python bridge` — **inconclusive, retry.** The EA was removed before it
  placed anything, so there was nothing to adopt. Correct behaviour, but it
  does not exercise the guard.
- **Two positions — stop.** That is the original bug and nothing below should
  be run until it is understood.

**Re-attach the EA afterwards** — demos 2, 4 and 5 need it.

---

## Demo 2 — a lost answer is not a "no" (stage3/020)

**The failure it prevents:** a signal whose send got no answer being handed
straight back to the scheduler, which retries it every 20 seconds.

1. Send a signal with the EA paused, **and** pull the bridge connection
   (close the bridge program) before the fallback can ask the broker anything.

**Expect:** the signal shows as **`unknown`**, not `pending`. No order is
re-sent. Leave it five minutes and confirm nothing else happens.

**[2026-09-01] There are two log lines, and which one you get tells you which
route ran.** Both are correct; note down which you saw.

- `[open] signal <id>: send outcome UNKNOWN (...) — parking, NOT retrying.`
  — the fresh-Telegram-signal route (`open_from_signal.py:63`). **This is the
  one that was broken and is most worth seeing**, per the note below.
- `[<source>] send outcome UNKNOWN (...) — parking signal <id>, NOT retrying.`
  — the auto-execute scan route (`scan_auto_execute.py:641`).

Seeing neither, with the signal back at `pending`, is the original bug.

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
2. Restart the app and wait for a reconciliation pass. **[2026-09-01, corrected
   during the session]** Every 12 monitor cycles — but the monitor loop is
   `asyncio.sleep(1 if fast_poll else 5)`, and with any trade open it
   fast-polls. So it is **about 12 seconds** with open trades and about a
   minute without. Measured on the live log, not read off the constant: the
   first version of this line quoted the 5 without checking which branch was
   running.

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

**Expect:** the trade stays **open** in the app and in MT5. **Nothing** appears
in history and no P&L is booked.

**[2026-09-01] The exact wording, so you know what you are looking for.**

The log line (an ERROR, not a warning — that was the old behaviour and it
hid this):

```
[Close] trade=<id> ticket=<n> NOT closed — broker refused the close: <error>.
Leaving it open in the database; reconciliation will settle it.
```

The Telegram alert:

```
*Close refused by the broker*
Ticket <n> was not closed: broker refused the close: <error>
The trade is still open and still managed. Nothing has been recorded as closed.
```

If the alert does not arrive but the log line does, the fix worked and your
Telegram alerting did not — a different problem, and not a reason to fail this
demo.

Then turn AutoTrading back on and confirm the next attempt closes normally —
that half matters just as much.

---

## Demo 5 — the breaker actually stops trading (stage3/050)

**[2026-09-01] Read this before you start it — as written, it contradicted
step 4 above.** Step 4 has you set the daily loss limit to 3%. On a demo
balance of, say, $10,000 that is a $300 ceiling, and one minimum-lot losing
trade will not come close. So:

1. **Temporarily** set the daily loss limit to a number one losing demo trade
   will breach — a few dollars' worth. Write down what 3% was before you
   change it.
2. Let a trade close at its stop.
3. Send another signal.
4. **Put the limit back to 3% before you finish.** This is the one step in the
   whole runbook that leaves your account misconfigured if you forget it, and
   it leaves it misconfigured in the dangerous direction only until the next
   broker day — after which a 0.05% ceiling would halt you on the first small
   loss every single day.

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
