# 017 — is your trading schedule in your clock, or the market's?

**Decision needed:** yes, one answer
**Money:** yes — it decides which hours orders are allowed
**Urgency:** matters now if the Mac and the VPS are in different timezones

## The two clocks

Your app reads time two different ways, and both are defensible on their own:

| | Clock | Where |
|---|---|---|
| **Sessions** — Asia / London / NY, news windows, the counter-bias windows | **UTC**, explicitly | the engines |
| **Trading Schedule** — the 7×4 windows you set in the UI | **the machine's own local time** | `check_trading_schedule` |

So when you type **09:00** into the Trading Schedule, the app means *nine
o'clock on that computer's clock*. When the Reversal Engine talks about the
London session, it means *08:00 UTC*.

## Why it matters more than it sounds

**The Trading Schedule is mirrored between the Mac and the VPS by the sync
link.** The setting travels; the clock does not.

So a 09:00–12:00 window set on a Mac in the UK becomes:

| Machine | Runs at (UTC) |
|---|---|
| UK Mac (winter) | 09:00 – 12:00 |
| US-East VPS | 14:00 – 17:00 |
| Singapore VPS | 01:00 – 04:00 |

If the VPS is the active trader — which it is under centralized signal
generation — **the schedule you set is not the schedule that runs.** It gates a
completely different part of the trading day, and nothing anywhere reports the
discrepancy.

It also drifts twice a year on its own: a machine on UK time moves an hour
against UTC at each clock change, while the session windows do not.

## What I need from you

**When you type 09:00 into the Trading Schedule, what do you mean?**

- **"Nine o'clock where I am."** Then the current behaviour is right for the
  Mac, and the VPS needs to be told your timezone rather than using its own.
- **"Nine o'clock market time (UTC)."** Then the schedule should read UTC like
  everything else, and both machines agree automatically.

The second is simpler and matches the rest of the app. But it is your
discipline, not mine — if you built those windows around your own day, saying
so is the right answer.

## What I did in the meantime

**Nothing that changes behaviour.** Changing which hours your orders are
allowed is not a decision I should make while you are asleep.

I added `tests/risk/test_schedule_clock.py`, which pins the current behaviour
and states the inconsistency in one place. It fails if the schedule quietly
moves to UTC, or if the sessions quietly move off it — so whichever way you
answer, the change is deliberate and visible rather than a one-word edit nobody
notices.

Related, and worth checking at the same time: the daily profit target and the
"rest of the day" reset both key off the same local clock, so they roll over at
the machine's midnight rather than the broker's.
