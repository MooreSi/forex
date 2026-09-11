# 028 — Should every client learn from every other client?

**Status:** **ANSWERED 2026-09-11.** *"I dont want to share trade data with
other users of the app just the learned ml engine as it develops."* So the
plan changes: **ship the trained model, not the training rows.** Still not
urgent, and still recommended to wait — see *Your answer, and what it changes*
at the bottom. Nothing is built.
**Money:** yes, indirectly. It changes what the Reversal Engine's ML learns
from, and the ML decides which trades are allowed to execute.
**Raised:** 2026-09-08, from your own request.

## What you asked for

That remote clients get the benefit of the trained data straight away, that it
refreshes when the app updates from GitHub, and that a client's own trading
still counts — sitting alongside the shared learning or merged into it.

## What can be done

It works, and it is smaller than it sounds. The engine's actual learning is
4,803 rows of numbers — 1.1 MB, a few hundred KB compressed. That can live in
the repo and arrive with the ordinary app update, because the app already
updates itself by pulling from GitHub.

**What cannot be done is committing the database itself.** It is 21 MB,
rewritten every few seconds, and it carries your Telegram and email settings.
(It has a slot for your MT5 login too. That slot is empty today — checked, not
assumed — but it is there.) Git keeps every version of a file forever, so that
would also grow to hundreds of megabytes within a month.

So: share the numbers, not the database.

## Decision 1 — how much should a client trust everyone else's data?

Each client would train on the shared rows plus its own.

- **A. Equal weight.** Simplest. A client with 50 trades of its own is
  effectively running the fleet's model — right for a brand-new client,
  arguably wrong for an established one.
- **B. Your own trades count for more** (say 3x). The shared data is a
  starting point, and your own market gradually takes over as you trade.
- **C. Shared data only until you have enough of your own**, then your own
  only.

**Recommended: B.** It is the only one that does both halves of what you asked
— useful on day one, and your own experience winning out later.

## Decision 2 — when

**Recommended: not yet.** Right now the shared data would be a record of a
system that loses $3.78 a trade. Three fixes in
`docs/todo/reversal-engine/` are specifically about changing that. Sharing it
today would spread the current problem to every client; sharing it after those
land spreads something worth having.

**Nothing has been built.** The design is
`docs/todo/reversal-engine/070-share-training-data-with-the-fleet.md`.


---

## Your answer, and what it changes

**One thing worth knowing, in case it changes your mind — and then I will stop
asking.** What the original plan proposed sharing was not your trades in any
recognisable form. Each row was a list of numbers describing the market at that
moment, plus one number for how the trade did. **No ticket, no account number,
no channel name, no balance, no prices.** Nobody could have read it and learned
anything about you, your broker or which channels you follow.

If you would rather not hand over the raw material of your edge regardless,
that is a perfectly good reason and the answer stands. It just costs more than
it looks, and here is what.

### It still works — three of the four things you asked for come free

A new client arrives already knowing what your engine has learned, it refreshes
with the ordinary GitHub update, and its own trading still counts. Nothing
about the promise changes.

### What it costs

**1. Your learning and theirs never actually merge.** With rows, a client
retrains one model that has learned from both. With a model, the client runs
**your** model and **its own** side by side, and blends the two answers by a
weight. It starts fully on yours and shifts to its own as it accumulates
trades. That is close to what you asked for, but it is two opinions being
averaged rather than one thing that learned from everything.

**2. It becomes a recurring job rather than a one-off.** Whenever the engine
learns to look at something new — a feature is added — every trained model is
thrown away by design and rebuilt. A model shipped before that change stops
applying to clients after it, **silently**. So every time the engine changes in
that way, somebody has to export a fresh one, or the fleet quietly goes back to
learning from nothing. Rows would have survived those changes untouched.

**3. It touches the part that decides which trades are allowed.** The blend
happens inside the function that scores a signal, so this is a money-path
change and wants a demo. Sharing rows would have been a change to what the
model trains on, not to how it decides.

None of that makes it wrong. It is your edge and your call — it just needs
saying that the cheap version was the other one.

### The recommendation that has not changed: not yet

Right now the model has correctly learned that the engine's signals lose money
— it scores the average trade at **-0.083R**. Shipping it today installs that
conclusion on every client. Three fixes are specifically about changing what it
learns. Build the plumbing whenever you like; **export the first shared model
after those land.**

The revised design is
[docs/todo/reversal-engine/070](../todo/reversal-engine/070-share-training-data-with-the-fleet.md).
