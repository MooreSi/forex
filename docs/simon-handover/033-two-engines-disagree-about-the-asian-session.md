# 033 — Two engines hold opposite rules about the Asian session

**Status:** open, **for your decision**. A switch has been built for one
half of it and left OFF; nothing is changed on either engine.
**Money:** yes — it decides which trades the Reversal Engine refuses
overnight, which is its busiest window.
**Found:** 2026-09-12, measuring the trend gate by session.

## What the trend gate was turned on for

You turned **Only trade with the trend** on for the Reversal Engine on
2026-09-09. The evidence was strong and it is still right: across every
executed signal, trades with the higher-timeframe bias were the only
profitable group on the account, and 2026-09-08 was a day the system bought
a falling market 46 times for -$1,270.89.

That measurement was taken across all hours together.

## Split by session, it reverses

Over all 5,414 reversal-engine signals on record:

| session | trades WITH the trend | trades AGAINST it |
|---|---|---|
| Asian, 00-07 UTC | 693 at **-$6.26** each, CI [-9.40, -3.12] | 621 at -$0.50 each, CI [-3.69, 2.69] |
| everything else | 1,480 at -$1.02 each, CI [-3.30, 1.27] | 1,154 at **-$4.81** each, CI [-7.48, -2.14] |

The two bolded numbers hold their sign in both halves of the period; the
other two do nothing but straddle zero, which means "no measurable
difference from nothing", not "slightly bad".

Read plainly: outside Asia the gate refuses the group losing $4.81 a trade,
which is what you turned it on for. Inside Asia it refuses the group losing
nothing and lets through the group losing $6.26 — roughly **$5.76 a trade
across 1,314 signals**, pointing the wrong way.

**This is not a case for trading counter-trend in Asia.** -$0.50 with an
interval straddling zero is not an edge. The most the evidence supports is
standing the rule down there.

**And the caveat matters:** almost all of that P&L is the engine's own
simulated ledger. Only a minority of signals ever reach the broker, so this
is the population the engine models, not a realised account curve.

## What has been built, and it is off

A new switch on **Signal Generator > Reversal Engine > Capabilities**:

> …but not in the Asian session: ignore the trend there

It does nothing unless **Only trade with the trend** is also on. When both
are on, the Reversal Engine stops refusing counter-trend trades between
00:00 and 07:00 UTC and behaves exactly as it does today at every other
hour. It is off, it has never been demoed, and it changes nothing until you
turn it on.

Worth knowing: that path refuses a counter-trend trade in **two** places —
your gate, and an older `level_score < 0.75` rule beside it. While your gate
is on the second one never changes an outcome, because the first already
covers every case it would catch. The switch stands both down together; had
it stood down only your gate, it would have quietly meant "counter-trend in
Asia, but only on strongly-scored levels", which is not what it says.

## The question that is actually yours

**The Bounce engine already does the opposite.** It has a rule —
`Asian counter-bias block: only trend-aligned signals in Asian session` —
that has been there since before any of this was measured, and it says
exactly what the Reversal Engine numbers above say is wrong.

So one of three things is true, and only you can say which:

1. **The two engines genuinely differ.** They trade different setups; it is
   possible the Asian session rewards one and punishes the other. If so,
   both rules are right and this should be written down as intended rather
   than left looking like an accident.
2. **The Bounce rule was never measured** and is inherited belief. If so it
   is costing money in the same way, and it should be measured the same way.
3. **The reversal-engine numbers are an artefact** of the simulated ledger
   and should not be acted on until more of those signals have actually been
   filled at a broker.

Nothing was changed on the Bounce engine, and nothing will be without you
saying so.

## What I would do

Turn the new switch on for one Asian session on demo, with **Only trade with
the trend** left on, and compare that session against the last few. One
switch, one window, attributable afterwards. Leave the Bounce engine alone
until its own numbers have been pulled.

---

# The Bounce engine, measured (2026-09-12)

Option 2 above was *"the Bounce rule was never measured and is inherited
belief"*. It has now been measured, from that engine's own database. **It
survives.** On its own data the rule it holds is the right way round, which
means option 1 — the two engines genuinely differ — is the reading the evidence
supports.

## Its record, split the same way

All 100 closed Bounce signals, by session and by whether they agreed with the
H1 bias:

| session | side | n | average | 95% CI |
|---|---|---|---|---|
| asian | **with the bias** | 21 | **+$2.09** | [-24.92, +31.55] |
| asian | against it | 5 | -$27.94 | [-68.50, +1.18] |
| asian | no bias | 8 | -$31.90 | [-50.86, -12.90] |
| other | with the bias | 40 | -$12.31 | [-31.23, +8.69] |
| other | against it | 14 | **-$23.79** | [-35.78, -11.99] |
| other | no bias | 12 | -$11.77 | [-39.95, +19.52] |

Two things stand out, and they are the opposite of the Reversal Engine's table
at the top of this file:

* **Asian trend-aligned is the only positive cohort anywhere in this engine.**
  +$2.09 a trade — barely, and the interval straddles zero, so call it "not
  losing" rather than "winning". It is still the best thing this engine does.
* **Against-the-bias outside Asia is its worst real cohort**, -$23.79 with an
  interval that clears zero.

So the Bounce engine's Asian rule admits its best group and refuses its worst.
The Reversal Engine's gate does the reverse in the same hours. On the evidence
available, both rules are pointing the right way for the engine that holds
them.

## The rule is also working exactly as written

All five Asian against-the-bias trades were `liquidity_sweep` — the one pattern
the rule deliberately exempts. Nothing else got through. That is a clean
confirmation that the 49 refusals it has logged are the rule doing its job,
not a leak.

## How much to trust this

Less than the Reversal Engine's table, and that one already carried a caveat.

* **The samples are small.** 21 and 5, against 693 and 621. Every interval
  above is wide; two of the six are nowhere near significant.
* **It is entirely virtual.** Not a minority this time — **none** of these 100
  closed signals ever reached the broker. Every figure is the engine's own
  simulated ledger.
* **The engine has produced nothing since 2026-08-27**, so this record stops
  growing. See `docs/simon-handover/034`.

## What this changes about the question

The question is still yours, but it is now narrower. Option 2 is out: the
Bounce rule is not unmeasured belief any more, and its own numbers back it.
That leaves:

* **Option 1** — the two engines genuinely differ, and both rules are right for
  their own setups. This is what the data says. If you agree, the thing to do
  is write it down as intended, which is now done in the engines domain README
  so that the next person does not read it as an accident.
* **Option 3** — both measurements are artefacts of simulated ledgers, and
  neither should be acted on until more signals have been filled at a broker.
  Still entirely defensible, and it argues for leaving the new Reversal Engine
  switch off a while longer rather than for changing anything here.

**Nothing on the Bounce engine has been changed.** Its three counter-trend
gates were lifted into `services/test_signal/_gates.py` and pinned by tests on
the same day, which changed no behaviour — the old expressions and the new
functions were compared across every combination of their inputs.
