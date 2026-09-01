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
