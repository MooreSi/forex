# 010 — Characterize trade reporting

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same approach as packs 1-2's 010: characterize against the real `forex_trader.core.database`
module (`db_module`), using a temp file passed to `db_module.init()`.

## Tests first (TDD)

- `tests/core/test_trade_reporting_characterization.py`:
  - `get_open_trades` — returns only `status='open'` rows, newest `open_time` first;
    `tg_source` backfilled from the joined signal's `source_name` when not set on the trade
    itself; `claude_open`/`claude_close` JSON columns parsed when present, left alone on bad
    JSON (same pattern as `get_signals`'s `claude_commentary`).
  - `get_all_trades` — no filter returns all (up to `limit`), newest `open_time` first; `status`
    filter narrows correctly; `limit` is respected; same `claude_open`/`claude_close` parsing.
  - `compute_performance` — starting balance from the explicit param (was `self._cfg`); win
    rate/avg win/avg loss/profit factor from closed trades; max drawdown/run-up from the
    cumulative P&L walk; Sharpe/Sortino from trade P&L as returns (guarded for <2 trades);
    daily stats computed from local-calendar-day cutoff; `peak_balance` read from
    `app_config`, falling back to current balance when unset.

## What to do

1. Write the test file against `SimulationEngine`'s real methods (`get_open_trades`/
   `get_all_trades` need no `self`; `compute_performance` needs a minimal stand-in exposing
   `_cfg` — same `_FakeEngine` pattern as pack 1's `reset_simulation`).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from packs 1-2.

## Notes

14 tests written in `tests/core/test_trade_reporting_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed `get_open_trades`'s `tg_source`
backfill only fires when the trade's own `tg_source` is falsy (existing value never
overwritten). `compute_performance`'s `peak_balance` correctly falls back to current balance
when `app_config["peak_balance"]` is unset — characterized both branches.
