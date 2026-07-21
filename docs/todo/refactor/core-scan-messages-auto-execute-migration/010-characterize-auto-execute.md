# 010 — Characterize auto-execution flow

**Status:** Done (2026-07-20)
**Depends on:** none (reuses `core_open_trade.open_trade`, already
extracted and independently characterized)
**Real-money surface:** highest in the whole migration series -- places a
real MT5 order via `open_trade`; every test here fakes it.

## Decision

No separate original method exists for this block, so characterization
drives the whole `_scan_messages` for one scan cycle with a message that
clears sub-packs B/C's own classification/strategy-resolution first (real
GD2 signal text, `auto_execute_signals=1`), a fake bridge with a
controlled tick, `open_trade`/`get_open_trades`/`_check_pre_trade_filters`/
`_find_and_apply_instant_followup` faked so each test isolates this
block's own gating/execution logic. `_price_in_entry_range` and
`suggest_lot_size` are left real (both cheap, deterministic, and already
exercised correctly by every scenario without needing to be faked).

Every branch pre-traced via throwaway scripts first, given this is the
highest-stakes block in the entire migration.

## Tests first (TDD)

- `tests/core/test_scan_messages_auto_execute_characterization.py`:
  - IME follow-up already matched -> `open_trade` never called,
    `auto_executed=True` regardless (no new position opened, the existing
    instant trade was updated instead).
  - Max open trades reached -> skipped, no `open_trade` call.
  - No live tick -> skipped.
  - Self-managed strategy (Conservative): only the entry-zone shape is
    validated (signal TP/SL geometry ignored); pre-execution SL is the
    fixed `entry_mid ± CONSERVATIVE_SL_PT`, not the signal's own SL.
  - Zone already breached (price broke through the wrong side) -> skipped
    outright, not queued.
  - Price outside the zone but not breached -> queued `pending`, not
    executed this cycle.
  - Pre-trade R:R/directional-cap filter fails -> skipped.
  - Non-self-managed strategy, `validate_signal` fails -> skipped.
  - `open_trade` raises a "stood down" error -> silently handled (zero
    alerts), signal reverted to `pending`.
  - `open_trade` raises a circuit-breaker error -> its own message
    surfaces directly as the skip-reason, one alert sent.
  - `open_trade` raises any other error -> generic "Auto-execution
    failed" skip-reason, one alert sent.
  - Successful fill with `trade_result.get("executed_remotely")` true ->
    `auto_executed=True` but the final alert is suppressed entirely (the
    remote node already sent its own).
  - Gap-adjusted market entry (Gold Diggers 2.0 source, IME on, price
    just outside the zone within the channel's 10pt cap): all TP/SL
    levels shifted by the gap, executes at market instead of queuing.
  - EA-managed Conservative fill: post-fill SL/TP override writes the DB,
    calls `modify_order` on the live ticket, and calls `ea.update_trade`
    with the exact new TP1.
  - Normal (non-self-managed) in-zone fill -> executes with the signal's
    own SL, correct lot size.

## What to do

1. Write the test file using a fake bridge/`_tg_reader` and faked
   collaborators, calling `_scan_messages` via
   `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- `open_trade`
  and `bridge.modify_order` are always faked.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

15 tests written in
`tests/core/test_scan_messages_auto_execute_characterization.py`, all
green on the first run against unmodified `engine.py` after two
self-caught fixture issues: a fake `_tg_reader.get_group_name` returning
a hardcoded channel name regardless of which channel a test configured
(broke the gap-adjustment source-name match), and a manual
`patch.start()`/`patch.stop()` loop that proved flaky across repeated
calls within one script -- switched to a single combined `with` statement
for every trace and test, which was reliable throughout. No `engine.py`
bugs found in any of the fifteen branches.
