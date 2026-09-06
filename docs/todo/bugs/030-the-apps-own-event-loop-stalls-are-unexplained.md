# 030 — The app's own event loop stalls, and nobody has looked since July

**Status:** open, not yet investigated. Recorded 2026-09-05 so it stops being
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
