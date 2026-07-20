# 010 — Characterize email scheduler sweep

**Status:** Done (2026-07-20)
**Depends on:** none (reuses `core_orb_report` and `core_mt5_performance`,
both already extracted and independently characterized in earlier packs)
**Real-money surface:** none directly -- but the ORB section's
auto-execute path can place a real MT5 order via the already-extracted
`core_orb_report.orb_auto_execute`, which is faked in every test here (its
own order-placing behavior was already characterized in its own pack).

## Decision

Same `mock.patch("forex_trader.core.engine.datetime")` technique as
`core-gd-copy-research-migration`'s 010 doc -- both the ORB section's
`datetime.now(ZoneInfo("Europe/London"))` and the daily/weekly section's
bare `datetime.now()` read the same mocked return value, so a single fixed
datetime drives both gates per test (tests targeting one section pick a
datetime satisfying only that section's own hour/minute). Same
`asyncio.sleep`-second-call-flips-`_monitor_running`-False technique as
every prior no-separate-sweep-method pack. `build_orb_report`/
`_orb_auto_execute` (engine methods) and `compute_mt5_performance` (engine
method) are faked directly on the class; `claude_ai.generate_daily_analysis`
and every `email_service.*` function are faked at module level.

Every branch pre-traced via throwaway scripts first, given the number of
interacting gates across three independent sections.

## Tests first (TDD)

- `tests/core/test_email_scheduler_characterization.py`:
  - No provider configured (`smtp_host`/`resend_api_key`/`mailjet_api_key`
    all empty) -> nothing runs, no report built, no email sent.
  - ORB email: 08:15 Monday, `orb_report_enabled`, not yet sent today ->
    report built, chart+HTML built, email sent with the chart attached,
    `app_config["email_last_orb"]` set to today's date on success.
  - ORB auto-execute only (`orb_report_enabled` off,
    `orb_auto_execute_enabled` on): report still built (needed for
    auto-execute), `_orb_auto_execute` called with it, no email sent,
    `app_config["orb_auto_execute_last"]` set.
  - Send-time mismatch -> daily/weekly sections skipped entirely for the
    cycle (no email of any kind).
  - Daily email: default 18:00, weekday, active-trader node, not yet sent
    today -> `compute_mt5_performance(90)` called, Claude analysis
    requested and passed through to `build_daily_html`, email sent,
    `app_config["email_last_daily"]` set.
  - Daily, not the active-trader node -> skipped even if enabled/gated
    correctly on time/weekday.
  - Daily, Claude analysis raises -> caught locally (own inner try/except),
    `claude_analysis=None` passed to `build_daily_html`, email still sent.
  - Weekly email: Friday, active-trader node, not yet sent this ISO week ->
    email sent, `app_config["email_last_weekly"]` set to `{iso_year}-W{week:02d}`.
  - Weekly, non-Friday -> skipped even if enabled.

## What to do

1. Write the test file using faked engine methods + faked `claude_ai`/
   `email_service` module functions, calling
   `_email_scheduler_loop` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- the
  order-placing collaborator (`_orb_auto_execute`) is always faked.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

9 tests written in `tests/core/test_email_scheduler_characterization.py`,
all green on the first run against unmodified `engine.py` after fixing one
self-caught test-fixture bug (a faked `compute_mt5_performance` missing the
implicit `self` parameter when patched onto the class, silently swallowed
by the original code's own blanket `except Exception: perf = {}` -- caught
by an unexpectedly-empty `perf` dict in the trace, not an `engine.py` bug).
No `engine.py` bugs found; the server-local-vs-Europe/London `datetime.now()`
inconsistency between the ORB and daily/weekly sections is a pre-existing
observation, documented in the pack README, not changed.
