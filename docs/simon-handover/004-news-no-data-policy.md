# Q004 — When the news feed is down, keep trading or pause?

**Who answers:** Simon (this is a risk stance, not a technical choice).
**Status:** **ANSWERED 2026-08-25 — A**, keep trading when news is unknown
and log loudly. Recorded here because the body below still describes the
question as open.

The app trades as if the calendar were clear whenever
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

**ANSWER:** A — confirmed. Keep trading when news is unknown, and log it
loudly. (Simon, 2026-08-25)

> **Note added 2026-08-25 during the upstream merge — this changes the basis of
> the answer, in Simon's favour.** Two facts were not known when this question
> was written:
>
> 1. **At the fork point the blackout had never fired at all, on any data.** The
>    ForexFactory feed names its currency field `country`; both calendar parsers
>    read it as `currency`, so every event came back with currency `None`,
>    nothing matched the USD/XAU filter, and the blackout returned "clear"
>    forever — while looking healthy, because the fetch succeeded and the event
>    list was non-empty. Fixed upstream on 2026-08-06 (`9e8172e`). The same bug
>    pinned `news_proximity_norm` at 1.0 for every signal fed to all three ML
>    engines, so any model trained on that feature learned from a constant.
> 2. **"News unknown" is now a far narrower window.** `news_calendar.py` keeps
>    the last good payload in a disk cache that survives restarts, retries with
>    5/10/20-minute backoff capped at an hour, and when the calendar is genuinely
>    unavailable `check_news_blackout()` falls back to a hardcoded schedule
>    (FOMC days, NFP Friday, CPI Tuesday, top-of-hour) and **blocks** in those
>    windows. A feed outage no longer means flying blind.
>
> So option A now costs much less than the question implies, and option B would
> buy correspondingly little. **Revisit if** the loud logs show the remaining
> blind spot (cold cache *and* a release outside the hardcoded windows) actually
> occurring.
>
> **Follow-up to raise separately:** `_FOMC_DATES_2026` is a hardcoded year-
> specific date list. It goes stale on 2027-01-01 and the fallback quietly loses
> its FOMC coverage — the same silent-failure shape as the bug above. Needs
> either a yearly refresh task or a derived source.

