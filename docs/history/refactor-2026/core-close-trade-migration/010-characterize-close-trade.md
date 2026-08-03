# 010 — Characterize close trade

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** `close_trade`/`_close_all_ladder_legs` call `bridge.close_position` —
tested against a fake bridge only, never a real/demo account.

## Decision

Same DB approach as prior packs. `self._bridge` replaced by a fake test-double exposing async
`close_position(ticket)` and `get_account()`. `push_trade_closed` (ledger) and
`telegram_alerts.send_message` are called for real (not mocked) since both are confirmed safe
in a test DB: `push_trade_closed` only writes local tables and no-ops when the sync server
isn't running; `send_message` short-circuits before any HTTP call when `telegram_config.enabled`
is 0 (the schema default) — see README for the verification.

## Tests first (TDD)

- `tests/core/test_close_trade_characterization.py`:
  - `_get_trading_balance` — prefers live MT5 balance when the bridge returns one > 0; falls
    back to the local sim account balance; falls back further to `starting_balance` when the
    sim account itself is unset (edge case, probably unreachable in practice but characterize
    the fallback chain as written).
  - `close_trade` — raises when the trade isn't open; uses the live tick's bid/ask for BUY/SELL
    close price; falls back to entry price when there's no tick and no MT5 ticket; calls
    `bridge.close_position` for an MT5-backed trade and uses its returned close price; raises
    when the bridge reports an error or `success: False`; routes to `_close_all_ladder_legs`
    when any ladder leg is still open, skipping the normal single-ticket path entirely.
  - `_record_close` — computes `gross_pnl`/`net_pnl` via `pnl()`; updates the trade row, sim
    balance, and cascades the linked signal to `closed`; invalidates the TP cache and the two
    externally-owned dicts; updates the `peak_balance` app_config watermark only when the live
    balance exceeds the previous peak; calls the Risk Governor halt check only when
    `risk_governor_enabled`; calls the circuit-breaker outcome recording only when the trade
    has an `mt5_ticket` (never for a pure-simulated trade).
  - `_close_all_ladder_legs` — closes every still-open leg via the bridge, sums real P&L, skips
    a leg with no ticket or a rejected/failed bridge close, records one aggregate partial-close
    row plus the parent trade closed.

## What to do

1. Write the test file using `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to
   a fake test-double, `_tp_cache`/`_scale_out_last_fail`/`_tp_safety_net_last_alert` set to
   plain dicts, `_profit_sound_seq = 0`, `_cfg = {"starting_balance": 1000.0}`. Patch/stub
   `self.get_tick` to return a fixed fake tick (or `None` for the no-tick branch).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order is ever placed, closed, or modified — verified by the fake
  bridge's call log, not just by absence of errors.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs (this cluster routes writes through `db_module.to_db_thread()`).

## Notes

18 tests written in `tests/core/test_close_trade_characterization.py`, all green against
unmodified `engine.py` on first run. No engine.py bugs found. Confirmed no real or demo MT5
order is ever placed, closed, or modified anywhere: `_FakeBridge.close_position` is a plain
in-memory call-log recorder, and every test's assertions were checked against that log (e.g.
`test_close_trade_routes_to_ladder_legs_when_any_leg_open` confirms ONLY the still-open leg
ticket gets a close call, not the anchor ticket). Confirmed `push_trade_closed`/
`telegram_alerts.send_message` are safe to call for real in this test DB (verified by reading
their source in the README) rather than needing to be mocked.

Confirmed several subtle behaviors exactly as documented: the ladder-leg routing check happens
BEFORE the normal single-ticket path, so a partially-closed ladder trade never touches its own
anchor ticket via the normal path; `_record_close`'s peak-balance watermark only ever increases,
never decreases; the circuit breaker's outcome recording is gated strictly on `mt5_ticket`
being set (a pure-simulated trade with no MT5 presence never touches the consecutive-loss
counter, regardless of win/loss); the Risk Governor halt check is gated on
`risk_governor_enabled` and, when triggered, sets `trade_pause_until` via the already-fixed
(pack 1) atomic `rg_apply_halts_on_close`.
