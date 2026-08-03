# 010 — Characterize GD Copy research sweep

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none -- gates a nightly ML-feature research job, no
order placed/modified/closed.

## Decision

`datetime.now(ZoneInfo("Europe/London"))` controlled via
`mock.patch("forex_trader.core.engine.datetime")` with `.now.return_value`
fixed and `.side_effect` delegating to the real class (same technique as
`core-orb-report-migration`'s 010 doc; `ZoneInfo` itself is left real since
only `.hour`/`.minute`/`.strftime` are read from the mocked return value).
`telegram_research.run_nightly_research` is faked -- a large, separate-module
pipeline (Telegram history read, Claude synthesis, ML retrain, email),
already out of scope for this extraction. Called via the same
`asyncio.sleep`-second-call-flips-`_monitor_running`-False technique as
`core-max-tp-hit-migration`, since this loop also has no separate "sweep"
method to call in isolation.

Every branch pre-traced via throwaway scripts first.

## Tests first (TDD)

- `tests/core/test_gd_copy_research_characterization.py`:
  - Not exactly 22:00 -> no pipeline call, no dedup write.
  - `is_remote_node()` checked unconditionally every cycle, even outside
    the 22:00 window (an observed inefficiency, not changed).
  - Remote node (`is_remote_node()` true) -> no pipeline call even at 22:00.
  - Already ran today (`app_config["gdc_research_last"]` matches today's UK
    date) -> no pipeline call.
  - 22:00, local, not yet run today, pipeline returns `{"ran": True}` ->
    pipeline called with the engine instance itself (the pipeline needs full
    engine access); `app_config["gdc_research_last"]` set to today's date.
  - Pipeline returns `{"ran": False}` -> `app_config` NOT updated (allows a
    same-day retry next minute if the run didn't actually execute, e.g. no
    messages yet).
  - Pipeline raises -> propagates to (and is swallowed by) the loop's own
    outer `except Exception`, no crash, `app_config` not updated.

## What to do

1. Write the test file using a faked `run_nightly_research`, calling
   `_gd_copy_research_loop` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- this function
  never calls an order-placing collaborator at all.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

7 tests written in `tests/core/test_gd_copy_research_characterization.py`,
all green on the first run against unmodified `engine.py` -- every branch
pre-traced via throwaway scripts first. No `engine.py` bugs found.
