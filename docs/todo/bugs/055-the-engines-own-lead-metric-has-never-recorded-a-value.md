# 055 — The Reversal Engine's lead metric has never recorded a value

**Status:** found and **FIXED 2026-09-12**, test-first, five mutants killed.
Historical rows are not backfilled — see the bottom.
**Touches money:** no. It is the engine's own research telemetry.
**Severity:** the number that says whether this engine does the thing it exists
to do has read zero since the day it was built, and looked like an answer.

## What it is for

The Reversal Engine emulates Gold Diggers VIP / GD2. `re_correlation` scores
that every day:

| column | meaning |
|---|---|
| `re_correlated` | how many of today's signals matched a reference signal |
| `ref_predicted` | **how many of those this engine fired FIRST** |
| `avg_lead_time_s` | the signed mean lead — negative is ahead |

`ref_predicted` is the whole point. Matching a channel after it posts is
copying; matching it before is predicting.

## What it has recorded

```
ref_predicted    = 0     on all 51 days
avg_lead_time_s  = NULL  on all 51 days
```

Not "mostly zero". Zero and NULL on every row the table has ever held.

## Why

`_correlate` runs on a rolling 4-hour window and upserts **one row per day**.
Anything computed inside that loop is rewritten with the window's view on every
run, and by the evening the window no longer contains the morning's matches.

That failure was already known and already fixed — for one field. The code says
so in its own comment:

> *"Query actual daily counts from DB rather than from the rolling 4h window.
> The 4h window ages out confirmed signals within the same day, causing
> `re_correlated` to be overwritten to 0 once correlations are >4h old."*

`ref_predicted` and `avg_lead_time_s` sat four lines above that comment, still
computed from the loop, and were overwritten exactly as described. One fix, two
of the four fields.

## The fix

`reversal_engine_repo.today_lead_stats(now_ts=None)` answers both from the
day's own rows — signals created today with `correlation_confirmed=1` and a
delta — so nothing can age out of it. `_correlate` uses it for the upsert.

Eight tests, five mutants killed: the sign test that decides who fired first,
the `AVG` made absolute (which would report an engine 100s early and 100s late
as 100s early), `None` collapsed to `0.0` (which reads as "dead level with the
channel" — a finding, and untrue), the day window removed, and the
`correlation_confirmed` check dropped. That last one needed a row carrying a
delta without the flag: the two are written together today, so nothing else
could tell the difference.

`now_ts` exists so the tests do not depend on the date they run on.

## What it will show, and what is not repairable

From the next correlation cycle the column starts recording. The 51 historical
rows stay 0 and NULL: the per-signal deltas are still in `re_signals`, so a
backfill is possible, but it would rewrite 51 days of research history on an
engine the owner reads, and it is not needed to start measuring.

Worth watching once it has a few days: on 2026-09-11 the engine correlated
**5** signals against 54 reference posts, where comparable days ran 18-27. The
correlation rate has been falling since 2026-09-09 — 0.043, 0.0, 0.029 against
a steady 0.10-0.21 before it. Whether that is the engine changing, the channel
changing, or the correlator itself is a separate question, and the newly-live
lead metric is one of the few things that can help answer it.
