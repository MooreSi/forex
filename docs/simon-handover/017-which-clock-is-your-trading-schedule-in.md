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


---

## ANSWERED and IMPLEMENTED, 2026-09-01

> **"Keep the clock to UK time which is the timezone I am in so I can keep
> track of the time locally."**

Done. The Trading Schedule — the windows, the per-window strategy override, the
daily profit target's day boundary, and the day highlighted on the schedule
screen — all now read **UK wall-clock time**.

The important word is *UK*, not *local*. Before today it read the machine's own
clock, which happens to be the same thing on your Mac and is not on a VPS
elsewhere. Now the same instant gives the same schedule time on both, and 09:00
stays 09:00 on your clock through the March and October changes.

**Sessions are still UTC** — Asia/London/NY, the news windows, the counter-bias
windows. That is deliberate and now written down at the top of `schedule.py`
rather than being an accident nobody had noticed.

### No new dependency

`zoneinfo` would be the obvious tool, but on Windows it needs the `tzdata`
package, which this project does not install — and Windows is what actually
runs the app. `backend/src/utils/uk_clock.py` implements the two statutory
rules directly:

    BST (UTC+1) from 01:00 UTC on the last Sunday in March
    GMT (UTC+0) from 01:00 UTC on the last Sunday in October

That is about fifteen lines. What makes it trustworthy rather than clever is
the test: it cross-checks **every hour of a four-year span** against the real
timezone database on any machine that has one, which includes this one and CI.
It skips where there is no database rather than failing, since that absence is
the whole reason the module exists.

So if the UK ever changes its clock-change rules, that test goes red on the
next run here — it will not silently drift.

Six mutations, all caught: a week-early spring change, always-GMT, always-BST,
an inclusive autumn boundary (an hour late), a midnight rather than 01:00 UTC
transition, and the gate reverting to the machine clock.

### One thing left, and it is yours

The **balance report periods** (`cmd_report`, `period_totals`) still use the
machine clock for "today" and "this week". That changes which trades count in a
report rather than which trades are allowed, so I have left it alone — but if
you want those on UK time too, say and it is a five-minute change.
