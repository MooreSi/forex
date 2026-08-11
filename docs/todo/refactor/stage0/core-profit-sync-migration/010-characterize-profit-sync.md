# 010 — Characterize profit sync + close-full-after-TPs

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** `_close_full_after_tps` calls `bridge.close_position`
on a detected residual position -- a real MT5 order-close call, tested
against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs. `asyncio.sleep` is patched in
`_schedule_profit_sync`'s retry tests to avoid real up-to-30-minute delays.
`_record_close` (already extracted as `core_close_trade.record_close`) is
mocked when testing `_close_full_after_tps`'s residual-reopen path, isolating
this pack's own logic from that function's already-characterized behavior.

## Tests first (TDD)

- `tests/core/test_profit_sync_characterization.py`:
  - `_sync_profit`:
    - No deals at all (from either `get_position_history` or the
      `get_deal_history` fallback) -> returns `None`, no DB write.
    - Deals present but none are closing entries (`entry` not in `(1, 2)`)
      -> returns `None`, no DB write.
    - First-time sync (`mt5_profit` was `NULL`): computed MT5 profit differs
      from the app's own `net_pnl` estimate -> the simulated account balance
      is corrected by the difference, `net_pnl` updated to match.
    - Already synced (`mt5_profit` not `NULL`): the `mt5_profit` column is
      still refreshed to the newly computed value, but the balance
      correction is skipped (only ever applied once).
    - `get_position_history` returns nothing -> falls back to
      `get_deal_history`, filtered to just the deals matching this ticket's
      `position_id`.
  - `_schedule_profit_sync`:
    - Trade already has a non-null `mt5_profit` on the very first check ->
      returns immediately, `_sync_profit` never called.
    - Not yet synced, `_sync_profit` succeeds on the first attempt -> called
      once, no `asyncio.sleep`.
    - Not yet synced, `_sync_profit` fails twice then succeeds -> called
      three times total, with `asyncio.sleep` called twice (the 10s and 60s
      delays) between attempts.
  - `_profit_sweep`:
    - Picks up both `mt5_profit IS NULL` trades and zero-profit trades closed
      within the last 24h; skips already-nonzero-synced trades; a per-trade
      `_sync_profit` exception doesn't stop the sweep from processing the
      rest.
  - `_close_full_after_tps`:
    - No residual position found -> syncs profit, schedules the retry loop,
      sends the "all TPs hit" close alert, trade stays `closed`.
    - Residual position still open in MT5 -> reopens the trade record
      (`status='open'`, `remaining_lots` set to the residual volume) and
      attempts to close it via `bridge.close_position`; on success, calls
      `record_close` with `reason="all_tps_hit_residual"`.
    - Residual close attempt itself fails -> the trade stays reopened,
      `record_close` is never called, an alert is sent instead.
    - No `mt5_ticket` at all -> skips the residual check and profit sync
      entirely, goes straight to the close alert.

## What to do

1. Write the test file using a fake bridge (`get_positions`/`close_position`/
   `get_account`/`get_position_history`/`get_deal_history`), calling each
   method via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

13 tests written in `tests/core/test_profit_sync_characterization.py`, all
green on the first run against unmodified `engine.py`. No `engine.py` bugs
found.

Confirmed a genuine, non-obvious detail: `_sync_profit`'s final
`UPDATE ... SET mt5_profit=?` runs unconditionally regardless of whether the
balance-correction guard fires -- so calling it again on an already-synced
trade still refreshes the stored `mt5_profit` figure to whatever MT5 reports
now (useful if the broker's own reported P&L changes slightly after the
fact, e.g. a late commission adjustment), it just never re-corrects the
simulated account balance a second time.
