# 010 — Characterize _handle_orb_fixed

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** closes an open position via `bridge.partial_close` -- tested against a
fake bridge only, never a real/demo account.

## Decision

Same fake-bridge approach as prior packs, extended with `partial_close` call-log capture.

## Tests first (TDD)

- `tests/core/test_handle_orb_fixed_characterization.py`:
  - No TP1 hit -> no-op, no bridge call, no DB write.
  - TP1 hit, no remaining lots (already fully closed) -> no-op.
  - TP1 hit, `mt5_ticket` set: calls `bridge.partial_close(ticket, remaining_lots)`; uses the
    bridge's returned `close_price` when successful.
  - TP1 hit, bridge rejects the partial close (`error` or `success: False`) -> logs and returns
    without calling `partial_close_trade` at all (no DB write, no Telegram).
  - TP1 hit, no `mt5_ticket` (pure sim trade): skips the bridge entirely, still calls
    `partial_close_trade` with the signal's own `tp1` price.
  - Always closes the FULL remaining size (never a partial percentage) — unlike Scale Out's
    tiered schedule.

## What to do

1. Write the test file using a fake bridge (`partial_close`), calling
   `SimulationEngine._handle_orb_fixed` via `SimulationEngine.__new__(SimulationEngine)` with
   `_tp_cache = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order closed — verified via the fake bridge's call log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs (this handler routes through `db_module.to_db_thread()` via `_get_remaining_lots`/
  `_get_triggered_tps`).

## Notes

5 tests written in `tests/core/test_handle_orb_fixed_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed the handler always closes the
FULL remaining size in one shot (unlike Scale Out's tiered 40/30/20/10 schedule) and that a
bridge rejection aborts cleanly before any DB write or Telegram send.
