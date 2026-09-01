# 020 — Out of Hours still runs on UTC, unlike your schedule

**Decision needed:** yes, but small — and it may well be "leave it".
**Money:** indirectly. It decides which strategy manages a trade, not whether
one is taken.
**Urgency:** low. Nothing is broken; this is a consistency question.

## What changed and what did not

On 1 September the **Trading Schedule** moved to UK time, on your answer: the
windows are your day, so they should follow your clock.

**Out of Hours did not move.** Its window — the default is 22:00–07:00 — is
still read in UTC.

## Why that might be right

They are not the same kind of setting. The Trading Schedule is your discipline:
"I want the app trading between these hours of *my* day". Out of Hours is about
the market: the overnight stretch when spreads widen and moves are thin, which
is a fact about the market's clock, not yours.

Read that way, UTC is the correct choice for OOH and UK is the correct choice
for the schedule, and the difference is deliberate rather than an oversight.

## Why you might still want to change it

For four months of the year they disagree by an hour. If you set OOH to
22:00 thinking of your own evening, then between late March and late October it
actually starts at 23:00 your time — an hour of your night managed by the
normal strategy rather than the Out of Hours one.

It is the same confusion the Trading Schedule had. The difference is that the
schedule decides *whether* a trade is taken, and this decides *how it is
managed* — so getting it wrong costs less.

## The question

**When you set the Out of Hours window, are you thinking in market time or your
own?**

- **Market time (UTC).** Leave it. Nothing to do.
- **Your own clock.** I move it to UK time, same as the schedule — about
  fifteen minutes, and the UK clock module already exists.

## What is in place regardless

`get_effective_strategy` had no tests and half of it was uncovered — this is
the function that swaps the strategy, so a mistake in it means a trade managed
by rules you did not pick for that hour. It now has 32, including the
midnight-spanning window (a naive check gets nine hours a day wrong), the
holiday date range, and every malformed-configuration case falling back to your
configured strategy rather than raising inside the path that opens a trade.

The clock it uses is asserted in a test, so whichever way you answer, the
change is deliberate.


---

## ANSWERED, 2026-09-01 — and it changed the design

> "It should always be local time — so if I'm based in the UK use my local time
> based on the time of the year, and if there are other users in other
> countries use their specific local time."

That is a better answer than either option I offered, and it means yesterday's
UK-only change was aimed at the wrong thing.

### What I had got wrong

**The original code was not wrong about the clock.** A bare `datetime.now()` is
the machine's local time — which, on your own Mac, *is* your local time, with
daylight saving handled by the operating system, and it would have been a user
in Singapore's local time on their machine.

It was wrong about **one machine**. A VPS is not where its user is. Because the
Trading Schedule is mirrored between the Mac and the VPS, the setting travels
and the clock does not, so a 09:00 window set here gated a different part of the
day on a server abroad.

I fixed that by hardcoding UK. That works for you and is wrong for everyone
else — exactly what you have just told me.

### What it is now

A **trading clock** with two modes:

- **No offset set (the default).** The machine's own local time. Correct for
  every ordinary single-machine install, in any country, daylight saving
  included, and no timezone database needed.
- **An offset set.** That offset from UTC instead — for a machine that is not
  where its user is.

Offsets are in **minutes**, not hours, because India is +5:30 and Nepal +5:45,
and "other users in other countries" includes them.

The Trading Schedule, the schedule screen, the balance report and the emailed
daily report all read this one clock, so they cannot disagree with each other.

### Two things still to do, and one is a question

1. **There is no UI control for the offset yet.** The column exists and the
   code reads it; nothing sets it. Straightforward to add — say where you want
   it and I will.

2. **A fixed offset does not follow daylight saving on its own.** For your Mac
   that never matters, because it uses the machine's clock. For the VPS it
   would: set it to +60 for British Summer Time and it stays +60 in November.

   The clean fix is for the **Mac to tell the VPS its current offset** over the
   sync link — it already sends a heartbeat, so the VPS would follow your
   clocks automatically, including the changes. That is a small piece of work
   and I would rather do it than leave you a setting that quietly goes an hour
   wrong twice a year.

   **Shall I build that?**

### Out of Hours

Still UTC, and now the odd one out. Once the trading clock has a UI control the
sensible thing is to move OOH onto it as well — but that is a real change to
when a different strategy takes over, so it waits for your word rather than
riding along with this.
