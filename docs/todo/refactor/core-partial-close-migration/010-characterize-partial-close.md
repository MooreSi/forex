# 010 — Characterize partial close

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no MT5 calls in this method (see README) — pure DB accounting

## Decision

Same DB approach as prior packs. No bridge involved, so no test-double is even needed for
`partial_close_trade` itself.

## Tests first (TDD)

- `tests/core/test_partial_close_characterization.py`:
  - Raises `ValueError` when the trade isn't open (unknown trade_id, or `status != 'open'`).
  - Inserts a `vantage_partial_closes` row and updates `remaining_lots`/`realised_pnl`/`net_pnl`
    on the trade for a normal partial close.
  - Updates the sim account balance by the partial P&L.
  - Clamps `lots_to_close` to `remaining_lots` (can't close more than what's left).
  - Moves SL to breakeven when `reason == "TP1"`, `move_sl_to_be_after_tp1` risk setting is on,
    and the trade isn't already at breakeven — and does NOT move it a second time if already
    flagged.
  - Does NOT move SL to breakeven for a non-`"TP1"` reason, or when the risk setting is off.
  - Auto-closes the trade (`status='closed'`, `exit_reason='all_tps_hit'`) and cascades the
    linked signal to `status='closed'` when the partial close brings `remaining_lots` to 0 (or
    below, from a clamped-but-still-full close).
  - Return value shape: `trade_id`, `lots_closed`, `remaining_lots`, `partial_pnl`,
    `auto_closed`.

## What to do

1. Write the test file against `SimulationEngine.partial_close_trade`, using
   `SimulationEngine.__new__(SimulationEngine)` (no bridge/collaborator needed — the method
   only touches `db_module` and `self.pnl`, both already resolvable without `__init__`).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from prior packs. Note:
  `partial_close_trade` is `async` and routes its DB writes through `db_module.to_db_thread()`
  (like pack 5's `_get_triggered_tps`) — the db-worker-thread reset helper from pack 5's 010 is
  needed here too.

## Notes

10 tests written in `tests/core/test_partial_close_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed the method truly never touches
`self._bridge` — no fake bridge needed at all, only the db-worker-thread reset helper (since
`partial_close_trade` routes its write through `db_module.to_db_thread()`). Confirmed the
breakeven-SL-move guard correctly checks all three conditions (reason, setting, not-already-
moved) independently, and that clamping `lots_to_close` to `remaining_lots` combined with the
auto-close-at-zero path both fire together correctly when a partial close would otherwise
overshoot the remaining size.
