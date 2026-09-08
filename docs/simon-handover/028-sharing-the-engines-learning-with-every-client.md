# 028 — Should every client learn from every other client?

**Status:** open. Two decisions, neither urgent.
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
