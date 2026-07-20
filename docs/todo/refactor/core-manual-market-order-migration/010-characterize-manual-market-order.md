# 010 — Characterize manual market order

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** places an order via `open_trade` -- tested against a fake bridge only.

## Decision

Same fake-bridge approach as prior packs (`get_fresh_tick`/`place_order`/`get_account`/
`get_candles`).

## Tests first (TDD)

- `tests/core/test_manual_market_order_characterization.py`:
  - Raises on an invalid direction.
  - Raises when no live tick is available.
  - Explicit SL: used as-is when the distance from entry is plausible ($1-10% of entry);
    raises for an implausible SL (too close or too far).
  - No explicit SL + DPM enabled: ATR-based auto-SL (1.2x ATR, direction-aware); falls back to
    a fixed 8pt distance when ATR/candles are unavailable.
  - No explicit SL + DPM disabled: raises.
  - Lot sizing: explicit lot wins; else strategy-fixed lot; else risk-based via
    `suggest_lot_size`.
  - Creates a backing `vantage_signals` row (`status='active'`, source_name "Manual Market
    Order") so the trade's foreign key resolves.
  - Calls `open_trade` with the resolved direction/SL/lot/strategy/tp; returns its result.
  - Telegram notification and background commentary are scheduled for a locally-executed
    order; background commentary is skipped (but the Telegram send still fires) when
    `result.get("executed_remotely")` is true.

## What to do

1. Write the test file using `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to
   a fake test-double.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed — verified via the fake bridge's call log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

12 tests written in `tests/core/test_manual_market_order_characterization.py`, all green
against unmodified `engine.py` on first run (after fixing two of my own test-design mistakes
before the first run, caught by re-reading the source carefully). No `engine.py` bugs found.

Important characterized behavior: `take_profit` is stored on the created signal/trade row
(`tp1`) but does **not** automatically reach the broker-side MT5 order — `open_trade`'s own
`mt5_tp` resolution only sends a broker-side TP for `STRATEGY_BE_RUNNER` or an explicit
`mt5_tp_override`, neither of which `open_manual_market_order` ever passes. So a Trail Stop (or
any non-BE-Runner) manual order with a `take_profit` places with `tp=None` at the broker —
the TP is purely an in-app/DB-tracked target, not a resting order. Also confirmed the SL
sanity-check bounds (implausible below $1 or above 10% of entry) and the ATR-based
auto-SL/fixed-8pt-fallback branch both behave exactly as documented.
