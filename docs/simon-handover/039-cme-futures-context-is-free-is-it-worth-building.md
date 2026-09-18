# 039 — CME futures context is free. Is it worth building?

**Status:** open, **for your decision**. A switch exists; it is off and it is
wired to nothing.
**Money:** no subscription needed. The cost is build time, and the risk is
building something nobody has shown works.
**Found:** 2026-09-17, from your question about whether the Reversal Engine
could watch dark pools.
**Corrects:** an earlier version of this note said CME data was a paid
entitlement. That is true only of real-time streaming, which this engine does
not need.

## Dark pools, briefly

They cannot be watched here, and it is not a limitation of this app. Dark
pools are an equities thing: off-exchange venues that are obliged to report
their prints to a regulator's tape, which is why you can buy a "dark pool
ratio" for a share and not for gold. Spot gold and spot FX are
over-the-counter. There is no central tape, nobody reports anything, and the
non-displayed liquidity that exists sits inside banks who do not sell you a
view of it.

## The real gap this would fill

Your broker quotes spot XAUUSD as a bid and an ask. It never publishes a
**Last** — an actual completed trade at an actual size. That runs through the
whole app:

> Every number this system calls "volume" is **tick volume**: a count of how
> many times the quote changed. Not how much gold traded.

So a volume profile, a VWAP, anything that sounds like order flow, is reading
how busy the quote was rather than how much money moved. The code is honest
about it — `order_flow.py` tags every result with the method that produced it
— but no amount of better code fixes it. The data is not in the feed.

CME **GC futures** are the lit, centralised market where gold actually prints
size. Real volume, real open interest, one venue, publicly reported.

## What it costs: nothing

CME publishes daily volume and open interest for gold futures free on its own
site, as end-of-day reports. That is the data this would use. Real-time
streaming is the part that carries a subscription (roughly $7–15 a month per
exchange for a non-professional, depending on the vendor) and this engine has
no use for it: a reversal engine holding trades for hours does not need a
live tape, and 10-minute-delayed data is worse than useless for entry timing
anyway.

Free and also worth knowing about: **CFTC Commitments of Traders**, weekly and
public. Far too slow to time an entry, but it is real positioning data and it
would sit naturally beside the macro context the engine already reads.

## So what is the actual question

Not "will you pay for it". It is this:

> **Nothing in this repo has measured that futures volume or open interest
> predicts anything about this engine's trades.**

You have 6,036 recorded signals with timestamps. The honest order of work is
to pull the free daily GC series, join it to those signals, and measure
whether outcome varies with it — before writing a single line of ingest,
scheduling, failure handling or UI. That is a research question the existing
Research study is the right shape for, and it costs a session, not a
subscription.

If the answer is no, you have lost a session and gained a fact. If the answer
is yes, you build the feed knowing what it is for.

## What I have actually done

Added one switch: **Signal Generator > Reversal Engine > Tuning > Market
context > "Read CME futures context (not connected yet)"**.

It is **off**, and turning it on **changes nothing**. There is no CME feed in
this build — no client, no ingest, nowhere to put a futures volume if one
arrived. The switch records the intent and one accessor reads it; nothing
consumes that accessor.

That is the same shape as "Scale size by volatility and drawdown", which has
sat on the same card un-connected since 2026-09-11. The tooltip says so in the
app, and a test (`tests/risk/test_cme_context_switch.py`) fails if that
wording ever disappears — because the failure that matters is you turning it
on, seeing no change, and either concluding the app is broken or, worse,
believing a later decision was informed by CME data when it was not.

## What I need from you

1. **Do you want the measurement done?** Free, one session, answers whether
   any of this is worth building.
2. **If the measurement says yes**, do you want daily end-of-day GC data or
   are you interested enough in intraday futures flow to pay for real-time?
   Only the second costs anything.
3. **If you would rather drop it**, say so and I will take the switch out
   rather than leave a control that means nothing.
