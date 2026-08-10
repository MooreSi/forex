# Q004 — When news data is missing or stale, trade through or pause opens?

**Decision:** PROVISIONAL — keep today's behaviour (trade as if no news when the
feed is unavailable), but log it loudly so it's visible. Awaiting the brother.
**Who decides:** the brother (this is a risk stance).
**Consumed by:** review-august-08 phase2/060 (moving the news fetch off the event
loop).

## The question

The news-calendar fetch is being moved off the event loop (it currently blocks
for up to ~15s on every engine cycle). Once it's a background cache, live paths
read the cached snapshot and never wait. That raises a policy question the
current code answers *by accident*:

**When the news snapshot is missing or stale (fetch failing / never succeeded),
should the engines open trades as if there is no news, or pause new opens until
news is known?**

## Why it matters

Trading through an unknown news state means a high-impact release the app simply
didn't fetch won't hold it back — it opens as if the calendar were clear. Pausing
on unknown-news is safer but means an outage of the news source stops trading.

## Options

- **(a) Trade through unknown news (current de-facto), logged loudly** — no change
  in behaviour, just visibility. The provisional default.
- **(b) Pause new opens while news is unknown/stale** — safer, but a feed outage
  halts opening. Would be a real behaviour change (money-affecting) needing the
  brother's sign-off.

**Decision:**

## What's proceeding now

Phase2/060 ships option (a) — because it's the *current* behaviour and changing
it is a money decision. If the brother chooses (b), that's a follow-up, gated on
his sign-off, not folded in silently.
