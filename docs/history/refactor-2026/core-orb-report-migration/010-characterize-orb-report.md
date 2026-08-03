# 010 — Characterize ORB report

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** `_orb_auto_execute` creates a *pending* signal (via
`create_signal`, already-extracted, DB-only) -- never places, closes, or
modifies a live order directly. No bridge order calls anywhere in this cluster.

## Decision

`datetime.now(timezone.utc)` is controlled via
`unittest.mock.patch("forex_trader.core.engine.datetime")` with `.now.return_value`
set to a fixed value and `.side_effect` delegating to the real `datetime` class for
any direct construction — every scenario's exact expected numbers (POC/VAH/VAL,
entry zone, stop, target, backtest medians) were traced against unmodified
`engine.py` with concrete fixtures first, given the calendar-window and
volume-profile math involved (see each test's fixture for the exact traced values).
`_get_orb_target_multiple`/`_backtest_orb_target_multiple`/`create_signal` are
faked via `unittest.mock.patch.object` where `build_orb_report`/`_orb_auto_execute`
are tested in isolation from the sub-pieces that get their own dedicated tests.

## Tests first (TDD)

- `tests/core/test_orb_report_characterization.py`:
  - `build_orb_report`:
    - No tick available -> returns `None`.
    - Called before London has opened this cycle -> returns `None`.
    - No Asian-session candles available -> returns `None`.
    - Price still inside the Asian range -> `direction="inside"`, all
      entry/stop/target fields `None`, a descriptive `position_note`.
    - Bullish breakout: range/POC/VAH/VAL computed from the volume profile,
      entry zone clamped to a minimum stop buffer, stop/target/rr computed from
      the (faked) target multiple.
    - Bearish breakout: mirrored fields on the other side.
  - `_get_orb_target_multiple`:
    - Cached value present for today's date -> returns the cache, backtest never
      called.
    - Cached date is stale (not today) -> runs the backtest and persists new
      cache values (multiple, n, date).
  - `_backtest_orb_target_multiple`:
    - Enough clean-breakout days (>= 8 samples) -> returns the median multiple,
      `is_default=False`.
    - No clean-breakout days at all (every day breaks both directions, i.e.
      ambiguous) -> falls back to the 2.0 default with `n=0`, `is_default=True`.
  - `_orb_auto_execute`:
    - Not proceeding (not the active-trader node, not centralized) -> no signal
      created.
    - Proceeding but `direction` is `"inside"` (not bullish/bearish) -> no
      signal created.
    - Proceeding, bullish -> creates a pending `BUY` signal at the report's
      entry zone/stop/target, auto-bootstraps the `ORB/IVB Report (auto)`
      channel's strategy override to `orb_fixed` if not already set.
    - An existing strategy override is never overwritten.
    - `orb_lot_size` risk setting, when set, is passed through as the signal's
      lot size.
    - `create_signal` raising does not propagate -- a failure Telegram alert is
      scheduled instead.

## What to do

1. Write the test file using a fake bridge (`get_tick`/`get_candles_range`) and
   the datetime-patching approach above, calling the methods via
   `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified (this cluster creates
  DB-only pending signals, never touches the bridge for order placement).
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

16 tests written in `tests/core/test_orb_report_characterization.py`, all
green on the first run against unmodified `engine.py` -- every scenario's
exact expected numbers (POC=2398.25/VAH=2401.5/VAL=2398.0 for the standard
fixture, entry-zone min-buffer clamping to a single point [2406.0, 2406.0]
on the bullish side, backtest median of 1.5 across 17 weekdays for a
uniformly-shaped clean-breakout fixture) were traced against unmodified
`engine.py` first via throwaway scripts, given the calendar-window and
volume-profile math involved -- this avoided any iteration churn on the
final test file.

No `engine.py` bugs found. No recurring quirk from the trade-handler
series here (this cluster never partial-closes or moves an SL; its only
DB write with real-money adjacency is `_orb_auto_execute`'s pending-signal
creation, which is inert until the existing zone-fill watcher
(`_try_activate_pending_signals`, not part of this pack) later opens it).

Confirmed the entry-zone/stop clamp described in the code's own comment:
the raw volume-profile POC/VAH/VAL zone and the fixed-fraction stop are
computed from independent reference frames, so the min-entry-stop-buffer
clamp can collapse the zone to a single point when the profile's natural
zone would otherwise sit too close to (or the wrong side of) the stop --
exactly what the standard fixture's numbers exercise.
