# 010 — Characterize update signal

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order via `bridge.modify_order`/`ea_bridge.update_trade`
-- tested against fakes only, never a real/demo account.

## Decision

Same fake-bridge/fake-EA approach as prior packs.

## Tests first (TDD)

- `tests/core/test_update_signal_characterization.py`:
  - No allowed fields in `updates` -> `{"status": "no_changes"}`, no DB write at all.
  - Unknown/disallowed keys in `updates` are silently dropped; only allowed fields written to
    `vantage_signals`.
  - No linked open trade -> signal updated, `trade_updated: False`, `trade_id: None`.
  - Linked open trade, strategy in the no-propagate set (Conservative/Conservative
    Trial/Scalp Runner) -> signal updated, trade's own SL/TP left untouched.
  - Linked open trade, other strategy, no `mt5_ticket` (pure sim trade) -> trade's SL/TP
    updated in the DB, no bridge call attempted.
  - Linked open trade with `mt5_ticket`: new SL on the correct side of the fill price is sent
    via `bridge.modify_order`; a new SL on the WRONG side is silently dropped (not sent, `sl=
    None` in the modify_order call) but the DB row still gets the raw value.
  - Broker-side TP is only sent for `STRATEGY_BE_RUNNER` (highest populated updated TP), never
    for any other strategy.
  - EA-managed + healthy: `bridge.modify_order` is skipped entirely; `ea_bridge.update_trade`
    is called with the updated TPs instead.
  - EA-managed but unhealthy: `bridge.modify_order` IS called (falls back to direct MT5
    control) but the trade is still marked `managed_by == "ea"`, so `ea_bridge.update_trade` is
    also called.
  - Python-managed (no EA): `bridge.modify_order` called, `ea_bridge.update_trade` never
    called.

## What to do

1. Write the test file using `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to
   a fake test-double, `ea_bridge.set_instance(fake)` for the EA-managed scenarios.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order modified — verified via the fake bridge's/EA's call logs.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

14 tests written in `tests/core/test_update_signal_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed the subtle EA-managed-but-
unhealthy fallback: `_ea_managing` requires BOTH `managed_by == "ea"` AND
`ea.is_ea_healthy()` -- an unhealthy EA instance falls through to the direct
`bridge.modify_order` call (treating the trade as if Python-managed for that one call) while
`ea_bridge.update_trade` is STILL called afterward unconditionally whenever `managed_by ==
"ea"`, regardless of health. This means an unhealthy EA can end up with BOTH the direct
broker-side modify AND its own in-memory TP array refreshed in the same update -- a real,
if narrow, double-write path that's clearly intentional (comment: "the update_trade() call
below still correctly refreshes the EA's tp[] array") rather than a bug, since the two calls
touch different things (broker-side native SL/TP vs the EA's own on-tick comparison state).

Also confirmed a wrong-side SL is written to the DB row as the raw value even though it's
never sent to MT5 (`sl=None` in the `modify_order` call) -- the DB and the broker can
legitimately disagree here until a later correction, by design.
