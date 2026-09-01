# 021 — "Today" and "which day" were London's, for everyone

**Status:** fixed 2026-09-01. No decision needed from you; recorded because it
changes a number on a screen you read.
**Touches money:** no. It changes which day a closed trade is *filed under*,
never the trade, the P&L, or anything that places an order.

## What was wrong

Three surfaces decided what day it was by asking `Europe/London`, hardcoded:

- the monthly P&L calendar and its heatmap (which square a closed trade lands on)
- "today's P&L" in the performance stats (where today starts)
- the calendar's own idea of today and which month to open on

For you this is right by accident. For anyone else it is wrong in a way that
looks fine: a trade closed at 08:00 in Sydney went onto the previous day's
square, and their "today" began at 09:00 or 10:00 local having already counted
most of the previous afternoon.

This is the same thing you told me on 2026-08-31 — *"it should always be local
time... if there are other users in other countries use their specific local
time"* — showing up in a third place. The trading clock built for that answer
now decides the day boundary too.

## What you will see change

**Nothing.** Every figure on your machine is identical, and there are tests
pinning that: they run the conversion at UTC+01:00, British Summer Time, and
assert it produces exactly what the hardcoded `Europe/London` produced.

On the VPS it now follows whatever the trading clock says, which since the sync
went in is whatever your Mac says.

## What did NOT change, on purpose

Everything anchored to the **London market session** still says
`Europe/London`, and should:

- the ORB report and its 08:15 email — that is London *open*, not your morning
- the London-session breakout gates
- the Reversal Engine's nightly 22:00 sweep

The distinction is the whole point: "when does London open" is a fact about the
market and is the same for everyone; "what day is it" is a fact about you. A
trader in Tokyo wants the London Open report at London's open and their
calendar on Tokyo's days. There is a test asserting those files still name
`Europe/London`, so a later tidy-up cannot sweep them in by accident.

## One thing worth knowing

A *configured* offset is a fixed number, so a historical trade is dated using
today's offset rather than the one in force when it closed. Around a
daylight-saving change a trade closed within an hour of midnight can sit on the
neighbouring square. On your Mac this cannot happen — with no offset configured
the machine's own timezone is used, which knows its own history. It only
applies to a VPS with a number typed into the new Trading Clock control, and it
is a display detail on one trade, not a P&L error.

Nothing to do. Raised here only because you read these numbers.
