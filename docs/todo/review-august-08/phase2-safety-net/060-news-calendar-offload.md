# 060 — News calendar off the event loop; cache empty results

**Status:** not started
**Depends on:** none
**Touches money:** no (but it stalls the loops that manage money)
**Layer:** service/utils
**Leverage:** `ai_trade_analysis.py` already demonstrates the executor-offload pattern used in this
codebase — copy it

## Problem

`utils/news_calendar.py` performs up to ~15s of blocking urllib **on the event loop**, called from
all three engines' live paths (review backend Critical #5). During that stall nothing ticks — no
monitor loop, no UI, no signal processing. Line 49 never caches a `None` result, so a failing
fetch re-blocks every cycle.

## Decision

Fetch in a background thread/executor on a refresh interval; live paths read only the cached
snapshot and **never wait** — a missing snapshot returns "no news data" explicitly. Failed fetches
cache the failure with a shorter TTL (so an outage retries sanely, not every cycle). The engines'
behaviour on "no news data" must be decided consciously (see Notes), not inherited by accident.

## What must NOT change

- News-filter *decisions* given the same data — byte-identical (characterization-pinned).
- Fetch source, parsing, and the data shape callers see.

## Tests first (TDD)

- `tests/utils/test_news_calendar_async.py::test_live_path_never_blocks` — fake-slow fetch; a
  cached-read call returns in bounded time (event-loop probe, no sleeps) — behaviour
- `::test_none_result_is_cached_with_ttl` — failing fetch once → no refetch within TTL — regression
  (line-49 bug)
- `::test_stale_snapshot_flagged` — snapshot older than threshold reports staleness — surface
- `::test_filter_decisions_unchanged` — characterization: same fixture calendar → same allow/block
  decisions as pre-change capture — characterization
- `::test_no_data_policy_explicit` — empty cache → the decided policy (see Notes), asserted, with
  negative control — control

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Extract fetch+parse into a background refresher owning the cache (thread or runtime task
   alongside the existing 13); live calls become cache reads.
3. Cache `None`/error with short TTL; add staleness metadata.
4. Wire the no-data policy per the decision in Notes.
5. `python -m tools.checks all`.

## Where

- `backend/src/utils/news_calendar.py` — the refactor
- three engine call sites (locate via imports) — read-side swap

## Acceptance

- With the fetch endpoint blackholed (fake), the monitor loop tick time is unchanged vs baseline.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- **Open decision (owner):** when news data is missing/stale, do engines trade as if no news
  (current de-facto behaviour when the fetch fails fast) or pause opens? Trading-through-unknown-news
  is a risk stance. Recorded in QUESTIONS.md as a follow-up if not answered by build time — default
  ships current behaviour, flagged loudly in logs.
- This is also the model for any future outbound call on a live path: nothing on the event loop.
