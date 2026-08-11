# Q004 — When the news feed is down, keep trading or pause?

**Who answers:** Simon (this is a risk stance, not a technical choice).
**Status:** the app currently trades as if the calendar were clear whenever
the news feed can't be fetched — that behaviour has been kept (it's what the
app has always done) but it now logs loudly when it happens. You choose
whether to keep it.

## The situation, in plain terms

The app checks an economic-news calendar and stands aside around big
releases (rate decisions, jobs numbers). That calendar comes from the
internet. Sometimes the fetch fails — the source is down, the connection
drops.

**When the app doesn't know the news, what should it do?**

Example: it's 13:25, a big US release lands at 13:30, and the news source
has been unreachable all morning. With option A the app doesn't know about
the release and will happily open a trade at 13:29. With option B it opens
nothing while the news is unknown — but that also means a mere website
outage stops all new trades.

## Options

- **A. Keep trading when news is unknown, and log it loudly**
  *(current behaviour, kept as the default — nothing changed)*
- **B. Pause new trades while news is unknown or stale** *(safer around
  releases; the cost is that a feed outage halts opening until it recovers.
  This is a real behaviour change, so it would also go through the demo
  session before shipping)*

**ANSWER:**

