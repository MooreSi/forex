# 010 — Characterize fees, sizing, sim account, Risk Governor

**Status:** not started
**Depends on:** none
**Real-money surface:** no

## Decision

Characterize the 10 target methods (see README's table) against the REAL `forex_trader.core
.database` module (`db_module`) — not a temp isolated DB like the other packs, since this is
the app's actual shared schema (`vantage_simulation_account`, `vantage_simulated_trades`,
`app_config`, `vantage_risk_settings` tables etc.). Tests must use a temp file passed to
`db_module.init()` so nothing touches the real app data, but the SCHEMA and function names are
the real, shared ones — there's no per-domain isolation to lean on here.

## Tests first (TDD)

- `tests/core/test_fees_sizing_characterization.py` — `calculate_fees` (spread/commission/swap/
  slippage components, the `include_spread_cost`/`include_swap_cost` toggles), `pnl` (BUY vs
  SELL direction math), `suggest_lot_size` (risk-pct sizing, `max_lot_size` clamp, zero-distance
  edge case).
- `tests/core/test_sim_account_characterization.py` — `get_sim_account`, `update_sim_balance`
  (delta application), `reset_simulation` (balance reset, trades/partial-closes wiped, pending
  signals cancelled — confirm this 3-statement sequence is ALREADY atomic via the existing
  single `with db_module.db():` block, not broken like the other engines' bugs).
- `tests/core/test_risk_governor_characterization.py` — `is_trading_paused`, `_price_in_entry_range`
  (BUY/SELL zone logic), `_check_pre_trade_filters` (R:R filter + directional cap, including the
  `_RR_BYPASS_SOURCES` bypass), `_rg_day_start_ts` (broker UTC+3 day boundary), `_rg_size_and_check`
  (stop-width cap, risk-based sizing, hard ceiling, TP1 R:R floor with the GD-VIP/Adaptive-Runner
  exemption, directional cap), `_rg_check_halt` (daily loss limit, total drawdown from peak),
  `_rg_apply_halts_on_close` (confirm/document the 2-separate-call atomicity gap between setting
  `trade_pause_until` and `risk_halt_reason` — this is the one real bug in this pack's scope).

## What to do

1. Write all three test files against `SimulationEngine`'s real methods (instantiate a minimal
   engine or call via the class directly where `self` isn't actually used).
2. Confirm the `_rg_apply_halts_on_close` atomicity gap with a forced-failure test (same
   technique as the other packs' transaction tests) — proves it's real before "fixing" it in 020.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- The `_rg_apply_halts_on_close` gap is proven with a real forced-failure test, not just
  asserted from reading the code.
