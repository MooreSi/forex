# 037 — Should a price with a typed full stop be read as a price?

**Status:** open, **for your decision**. Nothing on the live path has been
changed.
**Money:** yes, but indirectly — it decides whether a mistyped signal becomes
a trade or is dropped.
**Found:** 2026-09-16, from an hourly warning in the log
(`docs/todo/bugs/061`).

## What happened

On 2026-09-14 at 15:30, Gold Diggers Scalping posted this:

```
Buy Gold Now

4284.5. - 4278.5

TP 4287
TP 4290
TP 4293
TP 4296
TP open

SL 4274
```

Look at the first price: `4284.5.` — someone typed a full stop after it. The
app's price reader takes everything that looks like part of a number,
including that full stop, and then cannot turn `4284.5.` into a number. It
raises an error.

That error was breaking the **reference-signal backfill** — the hourly job
that records what the professional channels said, for comparison against our
own engines. One bad message was stopping the whole job: 15 perfectly good
reference signals went unrecorded, every hour, for two days. **That half is
fixed.** The job now skips the one message and carries on.

## What I have not changed, and why I am asking

The same price reader is used by the **live** signal scan — the one that can
open a trade.

Gold Diggers Scalping is a reference channel, so nothing was at stake this
time: the live scan never looked at the message. But if a channel you actually
execute posts a signal with a stray full stop or comma, the live scan will
also fail to read it. It handles that safely — it logs the failure and moves
on — so the result is **the trade is silently not taken**.

So the question is which behaviour you want:

**Option A — leave it.** A mistyped price is refused. Nothing is ever traded
off a number the app could not read cleanly. The cost is the occasional
missed signal, silently.

**Option B — read through the punctuation.** Strip a trailing `.` or `,` and
read `4284.5.` as 4284.5. The signal above would then be tradeable. The cost
is that the app starts acting on messages it currently refuses, and I cannot
promise from one example that every such message is a genuine typo rather
than a genuinely garbled post.

**Option C — read it, but only to show you.** Parse it for the record and the
reference tables, and keep refusing to execute it. More code, and the
asymmetry has to be explained every time someone reads it later.

I would not make this change on my own judgement: it changes what the app is
willing to trade from, and the only evidence either way is a single message.

**ANSWER:**
