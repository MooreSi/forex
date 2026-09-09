# The demos — a runbook for one sitting

> **Grew from five to nine on 2026-09-07.** Demos 1-5 are the original stage3
> set. Demos 6-9 cover four money-path fixes made on 2026-09-04 that this file
> predated, all of them found live on your own account: a close booked at $0,
> the trade cap being bypassed, Global Harvest never firing, and one close
> being announced and counted twice. Every one is written, tested and
> mutation-tested, and none is finished until you have watched it.
>
> **Corrected 2026-09-07: it was six, not four.** bugs/012 and bugs/023 were
> also finished and also had no demo, and adding 6-9 without them was an
> undercount on my part. They are demos 11 and 12. Demo 10 covers the template
> Anchor Lot, which you answered on 2026-09-07.
>
> **Grew to eighteen on 2026-09-09.** Demos 13-18 cover the six filters added
> since: the trend gate and the instant-fill filter (both of which you turned
> ON that day, so this is the first sitting where they are live), the
> resting-order sweep, the parked-signal re-check, Enable SL Parsing off
> declining a follow-up, and a template being refused on a stale EA build.
>
> Budget about 2.5 hours for all eighteen, not 90 minutes. **Do demo 18 FIRST**
> — it is how you find out the EA build is stale before demos 8, 10, 12 and 15
> quietly run against the wrong one. **Demo 10 cannot be forced** — it waits
> for a real signal on one channel; read it early so you know not to change
> that channel's multiplier in the meantime.

**For:** Simon, at an MT5 terminal on the **demo** account
**Time:** about 2.5 hours for all eighteen
**Status of the code:** all eighteen fixes are written, tested and mutation-tested.
None of them is `done`, and none becomes `done` because a test is green. Each
needs the run below, on a terminal, with your eyes on it.
**Last checked against the code: 2026-09-09.** Every log line quoted below was
confirmed to still exist and to still be spelled that way, and the offline
demos were re-run (`tests/e2e/test_killer_demos.py`, 15 passed). Five things
had drifted since this was written; each correction is marked **[2026-09-01]**.

**The 2026-09-09 check found the guard itself had a hole.** The pinning list in
`test_runbook_matches_the_code.py` still covered demos 1-5 only, so seven
demos' worth of quoted output had been unguarded since 2026-09-07 — the drift
this file exists to catch, in the thing that catches it. All eighteen demos are
now pinned in both directions: the fragment must exist in the source *and* still
be quoted here.

## Why you are doing this rather than an agent

**Changed 2026-09-09.** Rule 1 used to forbid demo orders as well as live
ones, and that is why this file was written as instructions for you rather than
a transcript of someone having already done it. The owner relaxed it that day:
demo-account trading is now allowed for development and testing.

So parts of this runbook can now be driven by an agent. What still needs YOU is
anything the app cannot observe for itself — what MetaTrader actually shows on
the chart, whether the EA's own log says what we think, and whether the timings
hold on a real socket. Where a demo below has been driven by an agent, it says
so and gives the date; treat an undriven one as still outstanding.

What has been done instead: **demos 1-5** are driven end-to-end offline
against the fake broker, in
[`tests/e2e/test_killer_demos.py`](../../tests/e2e/test_killer_demos.py). Each
has a negative control, and each was verified by re-introducing the original
bug and watching the test go red — eleven mutations, all caught. Demos 6-18
are covered by unit tests and mutation testing rather than an offline
end-to-end drive; their quoted output is pinned by
`test_runbook_matches_the_code.py`. That proves the code paths join up. It does not prove the EA behaves as expected, that MT5
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

**[2026-09-01] DO NOT run this as written. The instruction below was wrong,
and following it would have looked like a failure.**

~~1. Send a signal with the EA paused, **and** pull the bridge connection
(close the bridge program) before the fallback can ask the broker anything.~~

Closing the bridge produces `httpx.ConnectError`, and that is in
`_NEVER_SENT` (`services/broker/mt5_client.py`) — the deliberately **safe**
branch. Nothing left the machine, so nothing was placed and retrying is
correct. The signal would go back to `pending`, which is right, and which
this demo's own "Expect" line calls the original bug.

To reach UNKNOWN the request has to be **already on the wire** when the
connection breaks. Stopping the bridge first cannot produce that.

### What was done instead, and why the live run was dropped

**Owner's decision, 2026-09-01: do not run this live.**

The part of this demo that genuinely needed a real network was never the
signal parking — the offline killer demo drives that end to end. It was the
premise underneath: **what does httpx actually raise when a send is cut off
mid-flight?** Every test of `_send_failure` built those exceptions by hand,
proving the branching while assuming the premise. If httpx raised
`ConnectError` for a mid-request disconnect, a lost answer would be
classified "never sent", the signal retried, and stage3/010's runaway is
back.

That was settled with real listening sockets instead of a real order
(`tests/services/broker/test_send_failure_against_a_real_socket.py`).
Measured:

| what happened | httpx raises | verdict |
|---|---|---|
| mid-request, server drops the connection | `ReadError` | **unknown** |
| mid-request, headers sent then gone | `ReadError` | **unknown** |
| connection refused (bridge stopped) | `ConnectError` | never sent, safe to retry |

The premise holds. Each test asserts the request actually reached the server
before the break, so "unknown" cannot pass on a connection that never got
that far. Four mutations, all killed, including adding `ReadError` to the
safe list and emptying the list entirely.

**The rejected alternative, recorded so nobody re-derives it.** A faithful
live run is possible: a small proxy on a spare port with the app's
`mt5_bridge_url` pointed at it, forwarding `POST /order` to the real bridge so
MT5 genuinely places the order, then dropping the connection before returning
the reply. Deterministic, no race. It was declined because it spends a real
order to confirm a `ReadError` that a socket has already confirmed. If it is
ever wanted, that is the design.

### If you do run it anyway

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

## Demo 6 — a close with no price must not become a $44,783 loss (bugs/025)

> **Offline coverage added 2026-09-09 (night).** The guard had no test at all
> until then. `tests/trading/test_a_priceless_close_is_not_booked_at_zero.py`
> drives the real `_on_trade_closed` handler with the broker and engine faked
> at their own boundaries, since the point is what happens when the two
> disagree. Three mutants die, including re-introducing the original bug
> (the guard removed entirely), which fails four of the five tests.
>
> **This does not close the demo.** It proves the code path; it does not prove
> what MT5 actually sends when a position vanishes during a disconnect, which
> is the part your sitting is for.

**The failure it prevents:** on 2026-09-04, ticket 1935433548 was reported
closed with no closing price. The app read the absence as $0.00, and with a
0.1-lot entry at $4478.35 it computed **-$44,783.50**, wrote it to `net_pnl`,
`realised_pnl` and your simulated balance, and fed it to the daily-loss and
give-back guards — which halt trading. The broker had no closing deal at all,
which is why the trade never appeared in Closed Trades.

**What produces it:** only the EA's restore path sends a close with no price
(`HandleRestoreTrade`'s `closed_while_disconnected`). Every real close comes
through `ReportTradeClosed`, which always carries one. So this is what a
bridge restart looks like when the EA has lost sight of a ticket.

1. Open one trade and let the EA take it (any strategy).
2. Restart the bridge, so the EA reconnects and re-sends its view of what it
   is managing. That is the same sequence that produced the incident.

**Expect — the app asks the broker before it believes the EA.** The guard
queries the broker for a closing deal, and only records an exit if one exists.
With no deal, the log reads:

```
[EABridge] trade_closed(...) for trade=... ticket=... carried no close price
and the broker has no closing deal for it — leaving the row open rather than
recording an exit at $0
```

and you get a Telegram message saying the trade **stays OPEN and unmanaged**,
with no P&L recorded, telling you to check MT5.

**Pass:** the trade stays open, your balance does not move, and nothing halts.
**Fail:** any exit recorded at $0.00, or any large negative P&L appearing for a
trade with no closing deal. Stop if you see that.

**Two things this demo does NOT cover, and you should know both:**

1. **The second guard was not built.** A `close_price == 0` check inside
   `record_close` itself is defence in depth, and `record_close` is the frozen
   close path, so it needs your sign-off separately. What you are testing here
   is the bridge-side guard, which stops the reported incident before
   `record_close` ever sees it.
2. **The row from 2026-09-04 is still wrong.** Ticket 1935433548 is still
   marked closed with `close_price` 0 and roughly -$44,783 debited. Repairing
   it — and checking whether `trade_pause_until` or `risk_halt_reason` were set
   off the back of it — is a separate decision, and nobody has touched your
   data. Worth doing before the sitting, so a stale halt does not make demo 9
   look like a pass for the wrong reason.

---

## Demo 7 — the trade cap now counts resting orders (bugs/026)

> **PASSED 2026-09-09, driven by an agent on the demo account.** Max Open
> Trades set to 2, a BUY LIMIT rested at 4300 (ticket 1973407311, market was
> 4400), one 0.01-lot market order opened, and the third attempt was refused:
> ```
> Max open trades reached (2) — 1 open, 1 resting at the broker, 0 being opened right now
> ```
> The breakdown accounts for the resting order, and the count is right — no
> over-refusal. Cap restored to 5 afterwards.
>
> **It also found [bugs/039](../todo/bugs/039-cancelling-a-signal-left-its-order-resting.md).**
> Cancelling the signal from Pending Signals said "Signal cancelled" and left
> the order live at the broker, holding a trade slot for its four-hour expiry
> and still able to fill. Fixed and re-verified on the same order:
> `cancel_pending_order: cancelled ticket=1973407311`.

**The failure it prevents:** you asked on 2026-09-04 *"the max open trades in
the risk settings is set to 3, why has it opened more trades?"* A resting
pending order consumed no slot at either end — not when placed, not when it
filled — so N resting orders became N open positions over any cap, with the cap
never consulted.

**This reverses your own earlier answer, deliberately.** On 2026-08-31 you
answered [012](012-should-a-resting-order-use-a-trade-slot.md) with **A**,
resting orders stay free. Your 2026-09-04 instruction — *"whether it is a
resting order or a market order the EA should manage the max number of
allowable trades as set within the gui"* — is **B**, and B is what now ships.
If you still want A, say so before this demo rather than after.

1. Set **Max Open Trades to 2** for the sitting, so you are not waiting on five.
2. Get one resting order onto the broker's book. The quickest way is the
   Trading page's **Market Order** tab, which also places limit orders
   (`open_manual_limit_order`) — set a price the market cannot reach in the next few
   minutes so it rests unfilled. The Limit Runner strategy produces one on its
   own if you would rather wait for a signal.
3. Open one ordinary position. You now hold **one position and one resting
   order: two slots**.
4. Send a third signal.

**Expect:** it is refused, and the refusal names where the slots went:

```
Max open trades reached (2) — <a breakdown of which slots are in use>
```

**Pass:** refused, and the breakdown accounts for the resting order.
**Fail, and this is the one to watch for — OVER-refusal.** If the app refuses
while you can see fewer than two things on the account, a slot has leaked: a
stranded `activating` claim or a stale `working` row nothing freed.
`release_stranded_activations` covers the first case. If that happens, note
what was on the account and stop — an app that refuses every trade is worse
than the bug this fixes.

5. **Put Max Open Trades back to 3** (or whatever you run) before you finish.

---

## Demo 8 — Global Harvest is a basket total, not per trade (bugs/027)

> **PASSED 2026-09-09, 14:49:59, driven by an agent on the demo account.**
> It happened unforced, on the live system, minutes after the v1.06 recompile:
> ```
> global harvest threshold reached (combined $55.6 >= $50.0 across 2 position(s)) -- closing all
> global harvest closing ticket=1970354612 ($19.6)
> global harvest closing ticket=1970299959 ($36.5)
> ```
> Neither position individually reached $50; together they did, and both
> closed. Under v1.05 neither would have been touched. The config push was
> confirmed separately in the EA's own log
> (`global config updated: harvest_enabled=true harvest_threshold=50.0`),
> which also closes handover/025.
>
> **Confirmed again at 20:19:15 on the owner's own $75 threshold**, this time
> across four positions and including a losing leg, which is the case the demo
> warns about:
> ```
> global harvest threshold reached (combined $78.1 >= $75.0 across 4 position(s)) -- closing all
>   ticket=1973249365 ($39.3)   ticket=1973242032 ($38.4)
>   ticket=1973240300 ($32.2)   ticket=1973182186 ($-31.1)
> ```
> That run also exposed
> [bugs/041](../todo/bugs/041-a-profitable-harvest-arms-the-circuit-breaker.md):
> the losing leg counted as a consecutive loss against the circuit breaker, so
> a basket that banked +$78.10 left the account one loss closer to a halt.

**Do this one FIRST if you are short of time, because it needs preparation the
others do not.**

**The failure it prevents:** Trading > Global Parameters had Harvest ON at $75,
the chart panel read `GLOBAL HARVEST: ON at $75.00 profit per trade`, and
nothing was ever harvested. It was never a delivery failure — the setting
reached the EA every time. The semantics were wrong: it closed each position
whose **own** floating profit reached the threshold, so six trades at $15 each
is $90 of open profit a $75 harvest never touched.

**Before the sitting — this will not work otherwise.** The fix is in the EA
(v1.06) and **has not been compiled**. Run `tools/deploy_ea.sh`, then open
MetaEditor and press **F7**. Confirm the EA on the chart reports **1.06**
before you start; if it still says 1.05 the compile did not take and this demo
will simply reproduce the old behaviour.

1. **Trading > Global Parameters** (the same card as Risk per trade, not the
   per-template Harvest field on the EA Templates tab — they are two different
   settings with the same name). Switch **Harvest** on and set **Profit
   threshold ($)** to something small trades can reach — **$10**, not $75.
2. Open **three** small positions on XAUUSD, none of which individually reaches
   $10 of profit, but which together exceed it.

**Expect** in the EA log:

```
[EABridge] global harvest threshold reached (combined $<total> >= $10
across 3 position(s)) -- closing all
```

followed by one `global harvest closing ticket=...` line per position.

**Pass:** all three close when the *combined* total crosses $10, not before.

**Know what you are agreeing to.** Closing the basket closes **every** position
on the symbol, including any that are individually losing. That is what banking
a combined total means — closing only the winners would leave the losers
running and bank less than the threshold that just fired. If that is not what
you want, stop here and say so; it is a one-line change of intent, not a bug.

**This one closes real positions.** Demo account only, minimum size.

---

## Demo 9 — one close is one alert and one outcome (bugs/028)

**The failure it prevents:** on 2026-09-04, ticket 1940612275 sent you the same
"Trade Closed" message twice. The balance was never double-paid — a
compare-and-set already prevented that — but the single loss was counted as
**two consecutive losses** toward the circuit breaker, which halts live
execution. So one stop-out could halt you for the cooldown, and the ledger
outcome was overwritten on every affected trade.

**What produces it:** the monitor loop's SL check runs on EA-managed rows too,
so it and the EA's own close event race on every stopped-out template trade.
Both used to announce and book.

1. Open a trade on an **EA template** strategy (this race only exists on
   EA-managed rows).
2. Set its stop loss close enough to be hit, and let it stop out. Do not close
   it by hand — a manual close does not produce the race.

**Expect:** exactly **one** Telegram "Trade Closed" message, and exactly one
loss counted. Whoever loses the compare-and-set says nothing at all.

**Pass:** one alert, one outcome, and the circuit breaker's loss count goes up
by one — not two.
**Fail:** two alerts for one ticket, or the loss counter moving by two. Check
the breaker's count directly rather than trusting the absence of a second
message; the alert and the counting are separate halves and only the alert is
visible.

**Not covered:** ledger rows already corrupted by this before 2026-09-04 are
not repaired. Any trade this hit had its consolidated outcome overwritten to
"be", and those stay as they are unless you decide otherwise.

---

## Demo 10 — a fixed Anchor Lot stays fixed (handover/026)

**Answered by you 2026-09-07 (option 1); built 2026-09-03 in `6f353d5`.**

**The failure it prevents:** a template whose Anchor Lot is 0.10 opened at
0.13, because the channel's 1.3x multiplier was applied on top of a lot the
template had deliberately fixed. Five trades in seven days at 30% more risk
than you set (ticket 1925815819 and four others).

**This one is an OBSERVATION, not a five-minute test, and you should know that
before you plan around it.** The bug only appears on the Telegram Auto route,
because that route stores a lot on the signal itself. A Market Order from the
Trading page does not go through it, so there is no way to force this demo —
you have to let a real signal arrive on the affected channel.

**What you can check right now, before any signal:**

1. Trading > EA Templates: confirm the template bound to Gold Diggers VIP has
   **Anchor Lot 0.10** and **Risk % 0** (a template with Risk % above 0 is
   deliberately NOT exempt — that path is risk-derived and the multiplier is
   meant to apply).
2. Trading > Strategy > Channel Strategy: confirm
   `Telegram Auto (Gold Diggers VIP)` still shows a multiplier of **1.3**. If
   it does not, the demo proves nothing — a multiplier of 1.0 gives 0.10
   whether the fix works or not, so you need the 1.3 in place to see it.

**Then, on the next signal from that channel:** the trade opens at **0.10**.

**Pass:** 0.10 with the multiplier still at 1.3.
**Fail:** 0.13 — the exemption did not engage. Stop and say so.

**Do not "fix" this by setting the multiplier to 1.0 before the demo.** That
was the workaround while the question was open; doing it now removes the only
condition that makes the demo meaningful.

**The five trades already opened at 0.13 are unaffected.** Nothing has been
retro-corrected, and nothing will be without you asking.

---

## Demo 11 — the Instant Entry switch turns OFF as well as on (bugs/012)

**The failure it prevents:** the Telegram panel's Immediate Market Entry
button could switch IME on and never off. A setting you cannot turn off is
worse than one that does not exist, because you believe you have turned it off.

**There is only ONE control, and that is deliberate.** A per-channel Instant
Entry switch was briefly added on 2026-09-05 and removed on 2026-09-07: it
wrote a column nothing reads, because your 2026-09-03 directive made IME a
single global feature. So this toggle is the whole of it — there is no second
switch to check.

1. Parsing tab: turn **Immediate Market Buy/Sell** on. Confirm it reads on.
2. Turn it **off**. Reload the page.

**Pass:** it is still off after the reload.
**Fail:** it comes back on, or the toggle refuses.

**Zero money risk in this demo** — no order is placed either way. It is here
because a stuck IME switch is what decides whether later demos mean anything.

---

## Demo 12 — an instant entry uses the template's own stop (bugs/023)

**The failure it prevents:** on a template-managed channel, an instant entry
placed a generic ATR-clamped provisional stop and told you it was "awaiting
follow-up" for a follow-up that would never arrive — silently ignoring the
`sl_pips` / `use_dynamic_atr` the template was configured with. Live on Gold
Diggers VIP, 2026-09-03: BUY at $4481.21, SL $4469.18 flagged "provisional 12.0
pts".

**This is the half of your 2026-09-07 answer that already exists.** You said
levels should default to the EA template's settings; for the instant-entry path
that is built. Precedence is `use_dynamic_atr` first, then `sl_pips`, then the
ATR-clamped fallback — the same order `resolution.py` uses everywhere else.

1. Pick a template-managed channel, with **Immediate Market Buy/Sell on**
   (demo 11 is how you confirm that toggle works), and a template with a
   non-zero **SL pips**.
2. Let a bare direction arrive, or send one to a test channel you control.

**Pass:** the order's stop sits at the template's configured distance, and the
Telegram alert names the template instead of promising a follow-up.
**Fail:** a stop at the generic provisional distance, or the words "awaiting
follow-up" on a template-managed channel.

**This places a real order.** Demo account, minimum size.

---

## Demo 13 — the trend gate refuses a trade against the bias (reversal-engine/010)

> **PASSED 2026-09-09, driven by an agent on the demo account.** Six
> counter-bias signals refused between 16:41 and 18:06, all SELLs against a
> bullish H4:
> ```
> [RE-Engine] bias gate blocked live exec RE-2A2BA7 -- htf now bullish vs direction=SELL
> ```
> This is the 2026-09-08 failure inverted: that day the system bought a falling
> market 46 times; here it refuses to sell a rising one.
>
> **Look for the RE-Engine wording, not the governor's.** Searching the log for
> "Higher-timeframe bias" returns nothing — the Reversal Engine logs its own
> line — and that nearly produced the conclusion that the gate was not running.
> The line also used to print `level_score=0.95 < 0.75`, which is false, because
> it credited the level-score bypass with a refusal the owner's gate had made.
> Fixed in bugs/038; it now names the rule that refused.

**The failure it prevents:** on 2026-09-08 gold fell from 4438 to 4391, the
system bought it 46 times, and the day lost $1,270.89. Measured over every
executed Reversal Engine signal on record, trades **with** the higher-timeframe
bias are 369 at 61.8% for +$101.41 — the only profitable group in the whole
history — while trades **against** it are 201 for **-$1,210.98**.

**You turned this on 2026-09-09.** It ships off, so this is the first sitting
where it is live. It now governs six paths, not one: the Reversal Engine,
instant entry, limit-order signals, the resting-order sweep, and the shared
open path — one function, because two implementations of "is the trend against
us" that can disagree is how this class of bug starts.

1. Trading > Strategy > Risk Settings: confirm **Only trade with the trend** is
   on.
2. Note the current H4 direction, then let a signal arrive on the opposite side
   (or send one to a test channel you control).

**Expect:** the trade is refused and the reason names the bias and the setting:

```
Higher-timeframe bias is bearish — a BUY runs against it.
(Trading > Strategy > Risk Settings: 'Only trade with the trend')
```

**Pass:** refused, with that reason, and a same-direction signal still trades.
**Fail, and this is the one to watch for — OVER-refusal.** If it refuses trades
*with* the trend, or refuses everything, the bias read is wrong rather than the
gate. Turn the setting off and raise it before the next session; a gate that
refuses everything looks identical to a quiet market.

**No order is placed on the refusal.** The control half places one.

---

## Demo 14 — a signal that fills instantly is ignored (reversal-engine/040)

> **PASSED 2026-09-09, driven by an agent on the demo account**, on both
> routes that carry the gate:
> ```
> 14:55:57 [PendingWatcher] Signal fa588c7c skipped — Filled too soon — 297s after the signal, under the 300s minimum.
> 15:09:10 [RE-Engine] Filled too soon — 170s after the signal, under the 300s minimum.
> 15:39:26 [RE-Engine] Filled too soon — 2s after the signal, under the 300s minimum.
> ```
> Wording matches this runbook verbatim. Note the PendingWatcher line repeats
> once a second until the window passes — noisy, self-limiting, and the same
> shape as the defect demo 17 turned up.

**The failure it prevents:** fills inside five minutes of the signal are 443
trades at **-$2,142**; fills at 5-15 minutes are 115 trades at 71.3% for
**+$1,041**. The split holds in July, August and September separately rather
than coming from one month or a handful of outliers.

**Empirical, with no established mechanism, and you should know that going in.**
The obvious explanation — "a fast fill means price was already through the zone,
so the level never held" — was tested and rejected: it separates the same
population into -$3.55 and -$2.91 a trade, which is nothing. The filter is kept
because the numbers are strong and consistent, not because the reason is
understood.

1. Confirm **Ignore signals that fill immediately** is on, with the window at
   **300s**.
2. Watch for a signal whose entry zone is at or next to current price.

**Expect:**

```
Filled too soon — 12s after the signal, under the 300s minimum.
(Trading > Strategy > Risk Settings: 'Ignore signals that fill immediately')
```

**Pass:** refused, and a signal that waits out the window still fills normally.
**Fail:** it refuses a signal that took several minutes — check the clock on the
machine against the broker's, since the window is measured from `created_at`.

**No order is placed.**

---

## Demo 15 — a resting order is withdrawn when the trend turns (reversal-engine/050)

**The failure it prevents:** a pending order sitting on the EA was placed
against one market and executed into another. It answers your 2026-09-09
question directly — *"if there is a pending/resting order ... does it
re-evaluate the order before executing?"* For EA-side resting orders it now
does.

**It cancels; it never closes.** The sweep only withdraws orders that have not
filled. An order that filled in the meantime is left alone — closing a live
position on a bias flip is a different decision, and not one that was asked for.

1. With the trend gate on, place a pending order in the direction of the
   current bias, on the demo account at minimum size.
2. Wait for, or wait out, an H4 bias flip.

**Expect** the order to disappear from the terminal, with:

```
[Resting] withdrew <trade_id> ticket=<n> — Higher-timeframe bias is ...
```

**Pass:** the unfilled order is gone and no position was opened or closed.
**Fail, and this is the serious one:** an already-filled position closes. That
is the boundary the code draws; if it is crossed, stop and raise it.

**This places a real pending order.** Demo account, minimum size.

---

## Demo 16 — a parked Telegram signal is re-checked when price arrives (bugs/034)

> **PARTLY VERIFIED 2026-09-09 — the mechanism, not the schedule branch.**
> The re-evaluation block runs on the parked-signal path, proved live by the
> fill-delay guard that sits three lines below the schedule check in the same
> block:
> ```
> 14:55:57 [PendingWatcher] Signal fa588c7c skipped — Filled too soon — 297s after the signal, under the 300s minimum
> ```
> **The schedule branch itself was NOT exercised.** It needs a closed trading
> window, and the window was open all session. Forcing it means editing the
> schedule's window configuration, which is a bigger change to a live install
> than a demo warrants — a setting was already mis-restored once that day.
>
> **When you run it:** the log line is `Signal <id> **held** — <reason>` for
> the schedule and news guards, and `skipped` only for the fill-delay one.
> Grepping for "skipped" alone misses the very branch this demo is about.

**The failure it prevents:** a Telegram signal waiting for its zone could sit
for an hour and then open inside a news blackout, or outside the trading
schedule. The Reversal Engine re-asked both at the moment of the fill; this
route asked neither.

**Three waiting states, and they were not treated alike.** The Reversal Engine
re-checked schedule, news, a fresh ML probability, bias and fill delay. The EA
resting order got the bias sweep in demo 15. The parked Telegram signal got
pre-trade filters only — and those are bypassed for templates.

1. Let a Telegram signal park awaiting its zone (a limit-style signal away from
   price).
2. Before it fills, close the trading schedule window — Trading > Strategy.

**Expect:** when price reaches the zone, the signal is skipped rather than
opened, naming the schedule.

**Pass:** skipped, and re-opening the window lets the next arrival trade.
**Fail:** it opens anyway, or it skips a signal with the window open.

**No order is placed on the refusal.**

---

## Demo 17 — Enable SL Parsing off means a follow-up cannot move your stop (bugs/032)

> **PASSED 2026-09-09, driven by an agent on the demo account** — on GOLD
> DIGGERS INSTITUTIONAL, the same channel as the original report:
> ```
> SL adjustment (tg_id=29402, via=learned_rule) to 4391.00 DECLINED —
> Enable SL Parsing is off, so stops are not taken from Telegram.
> ```
> **And it found a defect the offline tests could not.** The decline was
> correct and then repeated **4,099 times in 71 minutes**, once a second,
> because it returned before the claim that marks a message handled. Raised
> and fixed as [bugs/035](../todo/bugs/035-a-declined-sl-adjustment-looped-forever.md).
> This is the case for running these against a real terminal.

**The failure it prevents:** with the toggle off, this happened on your account
on 2026-09-09:

```
SL adjusted — GOLD DIGGERS INSTITUTIONAL
Trade 062f91ad (ticket 1969210518): 4391.65 → 4395.0
Source: learned rule
```

The toggle governed the stop parsed out of a **new** signal. A later message
saying "adjust SL to X" reached a different route entirely, which never asked.

**Off means declined, not substituted.** At entry the toggle substitutes a
template or fallback distance, because a trade must have a stop. Here the trade
already has one, so the instruction is simply refused — and the message is not
claimed, so turning the toggle back on while it is still buffered lets it be
honoured.

1. Parsing settings: turn **Enable SL Parsing** off.
2. With a trade open on a channel that posts SL updates, wait for one (or send
   one to a test channel).

**Expect:**

```
SL adjustment (tg_id=..., via=learned_rule) to 4395.00 DECLINED —
Enable SL Parsing is off, so stops are not taken from Telegram.
```

**Pass:** the stop in MT5 is unchanged, and turning the toggle back on lets the
next update through.
**Fail:** the stop moves, or an update is declined with the toggle on.

**Uses a trade you already have open.** Nothing is placed.

---

## Demo 18 — a template is refused on a stale EA build (bugs/033)

> **PASSED 2026-09-09, driven by an agent on the demo account.** After
> `tools/deploy_ea.sh` and F7 the EA reported
> `v1.06 (compiled 2026.09.09 14:43:48, MQL build 6182)` with no mismatch
> warning, and the header badge rendered `bg-green` reading "EA" rather than
> "EA STALE BUILD". The negative control arrived on its own: a template trade
> opened normally at 15:43:02 on the current build.

**The failure it prevents:** demo 8's own note. On 2026-09-09 you recompiled and
re-attached the EA, and the chart still ran v1.05 — Global Harvest reading "per
trade" and not summing the basket, so a $50 target never fired on three trades
holding $60 between them. `tools/deploy_ea.sh` had not been run first, so
MetaEditor rebuilt the copy already in its own Experts folder.

**Templates only, and that is the whole design.** An EA Template *is* an
EA-native management definition — there is no Python-managed equivalent to fall
back to — so the entire management of a template trade is whatever build sits on
the chart. The EA-portable strategies do have a fallback, and blocking them here
would silently reroute rather than refuse, hiding the problem instead of showing
it.

**Do this demo FIRST if you do it at all** — it is how you find out the build is
stale before demos 8, 10, 12 and 15 quietly run against the wrong one.

1. Look at the top-bar EA badge before anything else. Amber **EA STALE BUILD**
   means stop and run `tools/deploy_ea.sh`, then F7, then re-attach.
2. To see the refusal deliberately: with a stale build attached, let a
   template-managed channel signal arrive.

**Expect:**

```
EA Template refused: the chart is running EA v1.05 but this app ships v1.06.
A template is managed entirely by the EA, so a stale build would run it under
replaced logic. Fix: run tools/deploy_ea.sh, compile (F7) and re-attach the EA.
```

**Pass:** refused with that message, and after deploying and recompiling the
same signal trades normally.
**Fail:** it opens on the stale build, or it refuses after a correct deploy —
check the badge is green before blaming the gate.

**Unknown is not stale.** On a packaged install with no EA source to compare
against, nothing is blocked. That is deliberate.

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
- 030's repairers — report-only today; making them act is a decision about
  money moving without you watching

*(This list used to name [012](012-should-a-resting-order-use-a-trade-slot.md),
"should a resting order consume a trade slot", as still open. You answered it
on 2026-08-31 and then reversed it on 2026-09-04; the behaviour shipped and is
now demo 7. Removed 2026-09-07.)*

And these are decisions waiting on you that are not demos at all:

- [026](026-template-anchor-lot-is-being-scaled.md) — **a template Anchor Lot
  of 0.10 is being traded at 0.13.** Five trades in seven days at 30% more risk
  than you set. Two possible fixes that mean different things, and both change
  lot size on live trades, so neither has been applied. There is also something
  you can do immediately with no code change: set that channel's multiplier
  back to 1.0.
- [027](027-what-should-a-direction-only-message-do.md) — what a "BUY" with no
  numbers should do: ignore, show, or hold open
- [014](014-a-wildcard-fingerprint-nothing-uses.md),
  [020](020-out-of-hours-still-runs-on-utc.md),
  [023](023-strategies-are-not-ea-templates.md),
  [024](024-per-account-databases.md) — smaller, but 023 and 024 each block
  work you asked for
