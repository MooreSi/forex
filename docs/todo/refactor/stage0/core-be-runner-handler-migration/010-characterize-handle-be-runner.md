# 010 — Characterize _handle_be_runner

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` -- tested against
a fake bridge only.

## Decision

Same fake-bridge approach as prior packs.

## Tests first (TDD)

- `tests/core/test_handle_be_runner_characterization.py`:
  - ADX < 25 (ranging, with `dpm_candles` set) -> falls back to `_handle_scale_out` entirely
    (verified via its own observable effects — e.g. a partial close firing — not via a mock,
    since the real fallback function is what's under test here too).
  - No `dpm_candles` -> ADX gate skipped entirely, normal BE Runner logic runs.
  - No TPs defined on the trade -> no-op.
  - Price hasn't reached TP1 yet -> no-op.
  - Price clears TP1 only -> SL moves to entry price (rung 0 of the ladder → rung 1).
  - Price clears TP1 and TP2 -> SL moves to TP1's price (the ladder always lags one rung behind
    the highest cleared level).
  - SL already at or past the target rung (e.g. re-processing the same tick) -> no update, no
    `modify_order` call.
  - No `mt5_ticket` (pure sim trade) -> DB still updates the SL ladder, bridge never touched.

## What to do

1. Write the test file using a fake bridge (`modify_order`), calling
   `SimulationEngine._handle_be_runner` via `SimulationEngine.__new__(SimulationEngine)` with
   `_dpm_candles = None` by default.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order modified — verified via the fake bridge's call log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

8 tests written in `tests/core/test_handle_be_runner_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed the ADX-ranging fallback delegates
to the REAL `_handle_scale_out` (verified via its own tiered 40% partial close firing, not a
mock) rather than any BE-Runner-specific ranging behavior, and that BE Runner itself never
partial-closes anything — the SL ladder always lags one rung behind the highest cleared TP
(clearing only TP1 moves SL to entry; clearing TP1+TP2 moves it to TP1's price, not TP2's).
