# 034 — The Bounce engine has produced nothing for sixteen days, and its own tuner did it

**Status:** open, **for your decision**. Nothing has been changed.
**Money:** not directly — no Bounce signal has ever reached the broker. It is
about whether one of your three engines is working or quietly switched off.
**Found:** 2026-09-12, reading the live `test_signal.db` while measuring 033.

## The fact

The last signal the Bounce engine created was **SIG-0173, on 2026-08-27 at
05:15 UTC**. Sixteen days ago.

It has not been idle. In the sixteen days since, it found **514 entry
candidates** — cycles where it had something to judge — and refused every one:

| refused by | count |
|---|---|
| ML gate (`predicted_R` below the 0.00 floor) | 369 |
| quality score below 85% | 88 |
| conflicting open signal | 31 |
| Asian counter-bias rule | 25 |
| DXY gate | 1 |

(Cycles that found no candidate at all are excluded — there are thousands, and
they are the market rather than a gate.)

## It is not the market, and it is not the app

The **Breakout** engine, running on the same candles through the same bridge,
produced its most recent signal on **2026-09-11 16:36 UTC** and has made 114 in
total. So the silence is specific to Bounce, not a market with nothing in it
and not a bridge that stopped delivering.

Worth knowing while you are looking: Breakout's record is **-$1,233.51 over 113
closed signals**, and it too has never sent one to the broker. Neither of these
two engines has ever placed a real order.

## What changed on 2026-08-27

At **05:30 UTC**, fifteen minutes after that last signal, Claude's batch tuner
ran on ten closed trades and raised `min_quality_score` for the `range` and
`trend` regimes. The `neutral` and `volatile_chop` regimes had been raised on
2026-08-13.

All four are now at **0.85 — the maximum the safety clamp allows.** The
parameter's own default is 0.40.

From that moment the engine has produced nothing.

## The uncomfortable part: it may be right

The engine's realised record, over its 100 closed signals:

| session | n | average |
|---|---|---|
| asian | 34 | -$10.33 |
| london | 25 | -$0.53 |
| ny | 19 | -$8.16 |
| overlap | 20 | **-$36.79** |
| off | 2 | -$31.30 |

Its virtual balance stands at **-$317.80**. Only one cohort in the whole record
is positive — Asian-session trades aligned with the trend, +$2.09 a trade over
21 of them, and even that interval straddles zero.

The ML gate refuses on *"predicted_R = -0.2 < 0.00 floor"*. On this record that
is not a malfunction. A model trained on an engine that loses money in every
cohort predicting that the next trade loses money is the model working.

So there are two readings and they need different actions:

1. **The engine has correctly switched itself off.** It found no edge, and the
   quality and ML gates are doing exactly what they were built to do. Then the
   thing to fix is that **nothing tells you** — sixteen silent days look
   identical to sixteen quiet ones, on a panel that says "running".
2. **The tuner over-tightened.** Four regimes pinned at the clamp's maximum is
   the tuner running out of room rather than finding a level. Then the signals
   it is refusing are not all bad, and 0.85 should come down.

## What I did not do

Nothing. Lowering `min_quality_score` makes the engine trade again, and a
change that makes an engine trade is yours. It is also not urgent in money
terms: **no Bounce signal has ever been sent to the broker** — all 100 closed
rows have no MT5 ticket. This engine is entirely virtual today.

## What I would do

Two things, in this order.

1. **Make silence visible.** — **done 2026-09-12, in the log.** Every six
   hours, once the engine has gone more than two days without producing
   anything, its watchdog now writes:

   > `TestSignalEngine: no signal in 16 days — 514 candidates found and every
   > one refused, 369 by ml_gate`

   The log rather than a panel, because **this engine has no panel** — it was
   removed on 2026-09-02 — which is the reason nobody saw this for a
   fortnight. See `docs/todo/bugs/046`: it is running anyway.

   It stays quiet on the three cases that would train you to ignore it: under
   two days, an engine that has never produced a signal, and silence with
   nothing refused (that is a quiet market, not a gate). It counts a cycle as a
   candidate when the row carries one rather than matching a list of gate
   names, so a gate added next year is counted without anyone remembering to
   update it.
2. **Then decide the gates.** If you want it trading again, the honest
   experiment is one parameter at a time: drop `min_quality_score` back to 0.70
   and leave the ML floor alone for a week. If it stays silent, the ML gate is
   the binding constraint and that is a different conversation.

## Related

* `docs/simon-handover/033` — the Asian-session question, which is what I was
  measuring when this turned up.
* `docs/todo/bugs/045` — `allow_asian`, a tuned parameter on this same engine
  that is wired to nothing.
