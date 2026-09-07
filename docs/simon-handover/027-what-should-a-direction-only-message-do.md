# 027 — What should a "BUY" with no numbers actually do?

**Status:** **ANSWERED 2026-09-07 — a fourth option, not one of the three
below.** A bare direction should ENTER where an EA template is bound, using
the template's levels immediately and correcting them when a second message
arrives. NOT BUILT — this makes the app trade more often and needs a spec and
a demo. See *Answered* at the bottom.
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


---

## Answered 2026-09-07 — enter where a template is bound

**Your answer, in your words:** *"on parsing in parsing settings if 'TP/SL in
Second Message' is selected it uses these otherwise it defaults to the ea
template settings"* — plus, on the two follow-ups: a bare direction should
place an order **even when that channel's Instant Entry switch is off**, but
**only where an EA template is bound**; and when "TP/SL in Second Message" is
on it should **enter immediately on the template's levels and correct them when
the second message arrives**, rather than waiting.

That is none of A, B or C above. It is closest to C, but scoped to
template-bound channels and with the entry-now-correct-later rule attached.

### What is already built

**The levels half exists.** `docs/todo/bugs/023` made the instant-entry path
use the template's own stop — `use_dynamic_atr`, then `sl_pips`, then the
ATR-clamped fallback. It is tested and is demo 12 in
[013](013-the-five-demos-runbook.md). Your "defaults to the ea template
settings" is that behaviour.

### What is NOT built, and why it needs a spec

**The gate half changes how often the app trades.** Today a bare direction
executes only when the global Immediate Market Buy/Sell AND the channel's own
Instant Entry switch are both on. Your answer removes the second of those for
template-bound channels, so messages that are currently parked and ignored
would become live market orders. That is a real increase in trading frequency
and it is a money-path change: spec first, then test-first, then a demo.

Three things the spec has to settle, none of which your answer decides:

1. **What "a template is bound" means when the binding is indirect.** A channel
   can resolve a strategy through `channel_strategy_rec` rather than a direct
   selection. Does an AI-recommended template count as bound?
2. **What happens when the second message never arrives.** The position is
   already open on template levels. It just runs on them — which is the
   template's normal behaviour, and probably right, but it should be stated
   rather than assumed.
3. **Whether the per-channel Instant Entry switch still means anything.** If a
   bare direction enters regardless of it on template-bound channels, that
   switch now only governs non-template channels. The switch was added on
   2026-09-05 (bugs/024) precisely so you could see and control this per
   channel, and this answer narrows what it controls. That may be fine, but it
   should be deliberate.

**Nothing has been changed.** The app still ignores bare directions on channels
whose Instant Entry is off.


---

## The two remaining gates, answered 2026-09-07

Asked after the per-channel Instant Entry switch was removed (bugs/024
reverted), which narrowed the question to the global toggle and the template
binding.

**When the global "Immediate Market Buy/Sell" is OFF** — your answer: *"if ime
is off it will wait for the full signal and then execute the trade."* The
global toggle stays the master off-switch. A bare direction opens nothing; the
full signal, when it arrives, is parsed and traded through the ordinary path.
**That is what the app does today, so this half needs no change.**

**When the global toggle is ON and NO template is bound** — your answer: no
bare-direction entry. **This is a change, and it restricts current behaviour.**
Today any Telegram channel the app knows about enters on a bare direction when
the global toggle is on. The justification is sound: a bare direction carries
no levels, so without a template there is nothing authoritative to place the
stop from and it falls back to the generic ATR-clamped placeholder — which is
the thing bugs/023 was raised about.

"Bound" means a template you chose: the Trading Schedule window's pick or the
Channel Strategy selection. An AI recommendation or the global default does not
count (your answer, same day).

### What this leaves to build

One change: gate bare-direction entry on a template being bound by one of those
two routes. It makes the app place FEWER trades than today, never more, which
is the safe direction — but it is still the order-placement path, so it is
test-first and it wants a demo.

The entry-now-correct-later rule you gave earlier applies to what happens after
that gate opens, and the levels half of it already exists (bugs/023).
