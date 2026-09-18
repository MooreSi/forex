# 038 — Should a later loss re-open trading after the daily target is hit?

**Status:** open, **for your decision**. Nothing has been changed.
**Money:** yes, directly — it decides whether the app keeps trading after it
has made its number for the day.
**Found:** 2026-09-16, from your question about ticket 2031441425
(`docs/todo/bugs/064`).

## What happened on Wednesday

Your daily profit target is $200. Here is the day:

* **07:10** — the day's closed profit reached **$210.68**. The app stopped
  taking new trades. You can see it in the log, refusing signals with "daily
  profit target reached ($210.68 of $200.00) — resumes tomorrow".
* **11:09** — a small win, $212.80. Still stopped. Good.
* **19:32** — a trade closed at **-$27.00**. The day's total dropped to
  **$185.80**.
* And at that moment the app started trading again, on its own, without asking
  you and without you pressing the "resume" button.
* **20:12** — it placed the limit order you asked about, ticket 2031441425. It
  filled and won $56.56, taking the day to $242.36.

You did not override anything. I checked — the override flag was never set.

## Why it did that

The app does not remember that the target was reached. It asks, fresh, every
single time a signal arrives: *"is today's total at or above $200 right now?"*
At 07:10 the answer was yes. At 19:32, after the loss, the answer became no,
so it carried on as if the target had never been hit.

There is a second, uglier detail. That -$27.00 loss was **the app's own
enforcement**. A limit order slipped through, filled, and the schedule guard
immediately closed it to stop it running — booking the $27 loss on purpose, to
protect you. And that loss is exactly what pushed the day back under $200 and
switched trading back on.

So: the guard paid $27 to shut the door, and the payment opened the door.

## The decision I need from you

**Option A — once it's hit, it's hit.** The day's target is reached once, at
07:10, and that is the end of trading for the day no matter what happens
afterwards. Losses later in the day cannot bring it back. The "resume past
today's target" button stays the only way back in, and it stays your decision.

This is what the app's own message already promises when it stops — "resumes
tomorrow" — and it is what I would recommend. It is also what a daily target
is normally for: to stop you giving back a good day.

*Cost of choosing this:* Wednesday's $56.56 winner would not have been taken.
The day would have ended at $185.80 instead of $242.36. That is the honest
number and it went the wrong way for this argument.

**Option B — leave it as is.** The target tracks the live total, so the app
keeps working until the day is *currently* above $200, and re-opens whenever a
loss pulls it back under. In effect it tries to *finish* the day at $200 or
better rather than *stop* at $200.

*Cost of choosing this:* a bad run late in the day can undo the morning and
the app will keep trading through it, because every loss makes it more willing
to trade, not less. That is backwards from how a discipline cap is meant to
behave, and it is the mechanism by which a good day becomes a flat one.

**Option C — hit is hit, but with a give-back allowance.** Stop at $200 and
stay stopped, unless the day falls back by more than some amount you set — say
$50 — in which case allow trading again to try to recover it. A middle road,
but it needs a second number from you and it is the most code, so I would only
build it if you actually want that behaviour rather than as a compromise.

Whichever you pick applies to the **per-window** targets too — they are built
the same way and behave the same way.

## The separate thing I am not asking about here

There is a second, plainer fault in the same story: the part of the app that
places limit orders never checks the trading schedule at all. It placed 13
orders on Wednesday while the target was already reached. Eleven were caught
and pulled back seconds later by a cleanup sweep; one filled two seconds too
fast and became the -$27.00 above.

That one is a straightforward missing check, not a judgement call — the same
check the other four routes into the market already make. It still touches
order placement, so it needs a demo session with you rather than a quiet fix,
but it does not need a decision. Details in `docs/todo/bugs/064`.

**ANSWER:**
