# 010 — Characterize bridge watchdog check

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none directly -- calls `bridge.get_health()`/
`enable_autotrading()` (read/toggle a platform setting, not an order) and
the already-established `start_bridge_process` callable (process
management, not an order).

## Decision

`_start_bridge_process` faked directly on the class (same convention as
`core-bot-commands-infra-migration`). `telegram_alerts.send_message` faked
at module level. `asyncio.sleep` fully replaced with a logging stub that
records every requested duration and stops the loop after N calls -- this
pack cares about the *sequence of sleep durations*, not just whether the
loop ran, since CHECK_INTERVAL(60) vs STARTUP_WAIT(20) is exactly the
behavior under test. The restart-cooldown gate is exercised for free: real
wall-clock time between mocked-instant iterations is ~0ms, so a second
restart attempt within one test run naturally falls inside the 180s
cooldown without needing to mock `time.monotonic()`.

Every branch pre-traced via throwaway scripts first, given the
cross-iteration state and dual sleep durations.

## Tests first (TDD)

- `tests/core/test_bridge_watchdog_characterization.py`:
  - Stays connected -> `consecutive_fails` reset, no alert, sleeps
    CHECK_INTERVAL (60).
  - `health.get("status") == "connected"` (the OR-alternative truthy path,
    not just `connected: True`) -> treated as connected.
  - `get_health()` raises -> treated as disconnected (not a crash).
  - Single failed check (below `CONSECUTIVE_FAIL_THRESHOLD=2`) -> no
    reconnect/restart logic runs at all, sleeps CHECK_INTERVAL, no alert.
  - Threshold crossed, `was_connected` was `True` -> offline alert sent
    exactly once (`"MT5 bridge offline. Attempting automatic reconnect."`),
    `was_connected` flips to `False`.
  - Reconnect (`was_connected` was `False`, now connected) with
    `enable_autotrading()` returning already-enabled / freshly-enabled /
    still-disabled / raising -> four distinct reconnect alert message
    variants, each ending with the corresponding AutoTrading status
    sentence.
  - Threshold crossed, not inhibited, cooldown elapsed -> `start_bridge_process`
    called, `last_restart_at` updated; if launch succeeds, sleeps
    STARTUP_WAIT (20) instead of CHECK_INTERVAL; if launch fails, falls
    through to CHECK_INTERVAL.
  - Threshold crossed, inhibited (`_bridge_inhibit_reconnect=True`) -> no
    restart attempted, no offline alert sent, sleeps CHECK_INTERVAL.
  - Threshold crossed again immediately after a just-launched restart
    (still disconnected) -> cooldown not yet elapsed -> no second restart
    attempted, no duplicate offline alert (`was_connected` already
    `False`), sleeps CHECK_INTERVAL.

## What to do

1. Write the test file using a fake bridge (`get_health`/
   `enable_autotrading`) and a logging `asyncio.sleep` stub, calling
   `_bridge_watchdog_loop` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- this function
  never calls an order-placing collaborator.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

10 tests written in `tests/core/test_bridge_watchdog_characterization.py`,
all green on the first run against unmodified `engine.py` after one
self-caught test-fixture fix (the same missing-`self`-parameter mock issue
seen in earlier packs when faking `_start_bridge_process` on the class). No
`engine.py` bugs found.
