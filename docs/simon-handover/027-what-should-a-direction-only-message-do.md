# 027 — What should a "BUY" with no numbers actually do?

**Status:** open. One decision needed from you.
**Money:** potentially yes, depending on which option you pick — one of the
three below would place trades the app does not place today.
**Related:** `docs/todo/bugs/015`. The waste and the log noise are fixed; this
is the behaviour question underneath them.

## The situation

Some of your channels post a direction on its own, with no numbers:

> XAU USD SELL

No entry price, no stop loss, no targets. Fifteen characters. The full levels
usually arrive a minute or two later, sometimes as a second message, sometimes
as an edit to that same message.

Right now the app reads that message, works out that it is a direction with
nothing to act on, and moves on without recording it anywhere. That is
deliberate — there is nothing to trade yet.

## What went wrong because of it

Because nothing was recorded, the app had no memory of having seen it. It
picked the message up again on the next cycle, about once a second, and did the
same work again — for as long as the message stayed in view.

One 15-character SELL from Gold Diggers VIP was re-read **8,319 times in under
three hours** and was still going when it was found. Your log file was 47 MB.

**Both halves of that are now fixed** and no decision was needed for either.
The app logs the message once instead of thousands of times, and it now
remembers, for as long as it is running, that it has already looked at that
exact message and skips it. Nothing about trading changed.

## So what is left for you

The app still does not **record** these messages anywhere. It just quietly
ignores them. That means:

- Nothing on screen ever shows you that a direction-only message arrived.
- If the promised follow-up never comes, nothing tells you.
- If the app restarts, it forgets it saw the message and reads it once more
  (once — not thousands of times).

The original write-up suggested recording each one as a parked signal row. **We
looked at what that would actually do and it is not safe as written**, for two
separate reasons:

1. It would not help the follow-up find it. The follow-up matcher looks in a
   different place entirely, so a parked row would be invisible to it.
2. It would lose you a trade. Once a message has a row, the app treats any
   later version of it as an *edit*. For a row parked this way, an edit that
   adds the full levels updates the stored numbers and then stops, without
   trading. **Today that same edit is read fresh and traded.** So the
   "tidy-up" would quietly turn a taken trade into a missed one.

That is why nothing was recorded, and why this is your call rather than a
cleanup someone could just do.

## The options

**A. Leave it as it is.** (What the app does now.) Direction-only messages are
ignored and invisible. No trade is ever placed or missed because of them. The
noise and the wasted work are already gone.
*Cost: if a follow-up never arrives, you never find out.*

**B. Show them, but never act on them.** Record each one somewhere you can see
— a list of "direction seen, waiting for levels" — with the trap above avoided,
so a later edit is still read and traded exactly as it is today.
*Cost: a modest amount of work. No change to what gets traded.*

**C. Treat the direction as a signal to hold open.** Park it properly so the
follow-up completes it, the way a partial signal with an entry price already
works.
*Cost: this changes what gets traded, and would need a demo session before it
is trusted. It also has to answer a question you would need to settle first:
if the levels never arrive, how long does it stay parked?*

**Recommended: B.** It gives you the visibility that is genuinely missing
without touching what the app trades. C is worth doing only if you actually
want these messages to become trades on their own, which is a trading decision
and not a technical one.

## What we need from you

Just A, B or C. If C, we also need to know how long a direction should wait for
its numbers before it is dropped.
