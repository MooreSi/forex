# 010 — Characterize trading-action bot commands

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** `/close` closes a live order via `close_trade` (pack
10), `/marketbuy`/`/marketsell` place a live order via
`open_manual_market_order` (already extracted), `/activate` places a live
order via `open_trade` (pack 11) -- all three collaborators are mocked in
this pack's tests, same treatment as `open_trade` in the IME packs. `/report`
sends a real email via `email_service.send_email` and calls
`claude_ai.generate_daily_analysis` -- both mocked.

## Decision

`close_trade`/`open_manual_market_order`/`open_trade`/
`claude_ai.generate_daily_analysis`/`email_service.build_daily_html`/
`email_service.send_email`/`compute_mt5_performance` are all mocked --
already-extracted (or already-real, stable) collaborators whose own behavior
was or will be characterized elsewhere. Every branch's exact numeric output
was traced against unmodified `engine.py` via throwaway scripts first.

## Tests first (TDD)

- `tests/core/test_bot_commands_trading_characterization.py`:
  - `_cmd_close`:
    - No open trades -> early return, `close_trade` never called.
    - No args -> usage message, `close_trade` never called.
    - `all` -> closes every open trade, aggregates total P&L, one line per
      trade (including a per-trade failure line if `close_trade` raises for
      one of several).
    - Valid ticket number matching an open trade -> closes just that one.
    - Ticket number with no matching open trade -> error message, no close.
    - Non-numeric ticket -> usage error, no close.
  - `_cmd_activate`:
    - No pending (`status='new'`) Telegram signal -> early return.
    - Signal fails `validate_signal` -> rejected, no signal/trade created.
    - Valid signal, current price inside the entry zone -> creates the
      signal row, calls `open_trade` with the risk-sized lot.
    - Valid signal, current price outside the entry zone -> signal saved with
      `status='pending'` instead of opened, `open_trade` never called.
    - No live tick available -> signal created but left for manual
      activation, `open_trade` never called.
  - `_cmd_market_price_buy` / `_cmd_market_price_sell`: delegate straight to
    `open_manual_market_order` with the correct direction; a raised exception
    is caught and reported, not propagated.
  - `_cmd_report`:
    - No recipient email configured -> early return, nothing sent.
    - Configured, send succeeds -> confirms the recipient.
    - Configured, send fails -> reports the error message.

## What to do

1. Write the test file using a fake bridge and mocked collaborators, calling
   each method via `SimulationEngine.__new__(SimulationEngine)` with
   `_cfg = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — `close_trade`/
  `open_manual_market_order`/`open_trade` are mocked in every test, never
  given a real bridge to act through.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

18 tests written in `tests/core/test_bot_commands_trading_characterization.py`,
all green on the first run against unmodified `engine.py`. No `engine.py`
bugs found. Confirmed via a throwaway trace that `_cmd_report`'s Claude
analysis call fails silently (caught by the original's own try/except) when
`self._cfg` isn't set -- the pack's `engine` fixture sets `_cfg = {}` to
match what the real `SimulationEngine.__init__` always provides.
