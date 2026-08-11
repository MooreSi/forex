# 010 — Characterize read-only/toggle bot commands

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none -- every command in this pack is read-only or a
simple risk-settings/app-config toggle. No bridge order calls anywhere.

## Decision

Same fake-bridge approach as prior packs, extended with a fake `tg_reader`
object (`get_status()`) for `_cmd_status`. Formatting-heavy responses are
tested via substring assertions on the computed values (balances, signs,
win rates, pluralization) rather than full exact-string matching, since most
of each function's length is static text, not logic.

## Tests first (TDD)

- `tests/core/test_bot_commands_readonly_characterization.py`:
  - `_cmd_help`: returns the static command list (single smoke test).
  - `_cmd_balance`: MT5 account path (uses bridge balance) vs. simulation
    fallback path (bridge reports zero/no balance); open P&L included only
    when there are open trades, with correct sign and pluralization.
  - `_cmd_daily`: today's closed trades aggregated into win rate/best/worst;
    zero-closed-trades day shows "No closed trades today"; open trades
    section only appears when trades are open; MT5 vs. simulation balance
    fallback (same as `/balance`).
  - `_cmd_status`: strategy name resolution (DPM overrides the raw strategy
    display), pause state reflected when `trade_pause_until` is in the
    future, Telegram slot lines only appended when a `tg_reader` is present.
  - `_cmd_trades`: "No open trades." when empty; per-trade P&L/held-time
    formatting when open trades exist.
  - `_cmd_pause`: default (no args) pauses 1h; explicit `30m`/`2h`/`1d`/bare-number
    (minutes) suffixes parsed correctly; invalid duration returns a usage
    error without touching `app_config`.
  - `_cmd_resume`: clears the pause timestamp, reports auto-execute on/off.
  - `_cmd_risk`: no-args reads back the current setting; valid percentage
    updates it and reports the dollar amount at the current balance; out-of-range
    (outside 0.1-10%) and non-numeric values are rejected without writing.
  - `_cmd_strategy`: no-args lists the current strategy + menu; a known alias
    (e.g. `ct` for Conservative Trial) resolves and updates the setting; an
    unknown name is rejected without writing.
  - `_cmd_dpm_on`/`_cmd_dpm_off`/`_cmd_ime_on`/`_cmd_ime_off`: each flips
    exactly its own risk-settings flag.

## What to do

1. Write the test file using a fake bridge (`get_account`/`get_tick`) and a
   fake `tg_reader` (`get_status`), calling each method via
   `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — this pack has no
  order-placing surface at all.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

25 tests written in `tests/core/test_bot_commands_readonly_characterization.py`.
One self-caught test bug (asserted "Open Trades (1)" when the code correctly
singularizes to "Open Trade (1)" for n=1 -- fixed the assertion, not the
code). No `engine.py` bugs found.
