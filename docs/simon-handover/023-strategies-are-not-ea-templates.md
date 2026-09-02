# 023 — "convert the strategies into EA templates" is not a like-for-like swap

**Decision needed:** yes, before I can finish item 4 of your 2026-09-02 list.
**Money:** yes. It changes where stops and targets are placed, and whether a
signal enters at market or waits.
**Found:** 2026-09-02, investigating the request.

## What you asked for

> "trading > strategy parameters - we're now only using EA templates so remove
> this section and any strategies convert these into EA templates that can be
> selected."

I have done the safe half — the **Quick comparison** table is gone. I have not
removed the Strategy Parameters card or converted the strategies, and this is
why.

## The thing that makes it not mechanical

An EA template and a strategy do not do the same job.

**An EA template manages a trade that already exists.** Its 94 fields are all
about what happens after entry: trail, breakeven, the partial-close ladder,
grid legs, harvest, cancel-siblings. The EA reads them on every tick.

**A strategy also decides how the trade is entered.** Two examples from the
code, not from the docs:

- `services/signals/resolution.py` computes the SL and TP levels *per
  strategy*. Adaptive Runner asks for its own parameters there
  (`get_strategy_params(STRATEGY_ADAPTIVE_RUNNER)`) and derives different stop
  geometry from the same signal than Fixed R:R would.
- `services/signals/pending_activation.py` branches on the strategy to decide
  whether a signal becomes a **pending order that waits for a retest** or goes
  in at market — Reversal Runner, Adaptive Runner and Adaptive Runner 2 take
  that path; the others do not.

An EA template cannot express either of those. It is handed a trade after
those decisions have been made.

So "convert Fixed R:R into an EA template" has no faithful answer for the
entry half. Whatever I chose, some channel's trades would start entering at
different prices with different stops — silently, because the app would still
show a strategy name it recognised.

## Why I also left the Strategy Parameters card

It is the only place the SL/TP geometry those strategies enter with can be
tuned. Removing it while channels are still bound to Python strategies takes
away the control without removing the thing it controls — a functional
regression rather than a tidy-up. The two halves have to move together.

## What I need from you

Any of these is a decision I can act on:

1. **Which strategies are actually still in use?** If every channel you care
   about is already on a `Template: ...` selection, the built-ins can be
   retired outright and both cards can go. That is a five-minute check on
   Trading > Strategy > Channel Strategy, and it is by far the most likely
   answer given you said "we're now only using EA templates".
2. **If some channels still use a built-in strategy**, name them and I will
   build EA templates that match their *management* behaviour, and tell you
   for each one what changes about entry — because something will.
3. **Or: leave entry to the strategies and management to the templates.** They
   already coexist; the Strategy Parameters card would stay, and only the
   selection UI would be simplified.

I would not guess between these while you are asleep. Option 1 is very likely
right, but "very likely" is not the standard for something that moves where a
stop sits on a live trade.
