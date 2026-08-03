# 010 — Characterize signal resolution

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none in this pack's own scope (see README) — but characterizing it means
calling the full, unmodified `open_trade_from_signal`, which DOES place an order via
`open_trade` and, for 6 strategies, calls `bridge.modify_order` afterward (that's the pack 13
scope, unavoidably exercised here since the split doesn't exist in current `engine.py` yet).
All of it against a fake bridge only — no real/demo order ever placed or modified.

## Decision

Since the extraction split point doesn't exist in current `engine.py`, characterization calls
the full `open_trade_from_signal` (through a fake bridge) and reads the **pre-fill** resolved
values off the fake bridge's `place_order` call log (`sl`, `lots` as passed to `place_order`) --
these are exactly `stop_loss_to_use`/`lot_size` before any post-fill override runs, so they're a
clean signal for this pack's actual scope even though the strategies with post-fill overrides
immediately rewrite the DB row afterward. Strategy resolution itself is read from the returned
`result["strategy"]`.

## Tests first (TDD)

- `tests/core/test_signal_resolution_characterization.py`, organized by gate/branch (see
  README's bullet list for the full inventory): signal fetch/validate, circuit breaker, session
  gate, pre-trade filter, price zone, spread guard, channel pause, strategy resolution
  (override/auto/global default), lot sizing (override/signal/risk-based/channel-mult/fixed/
  age-decay), the 7 strategies' pre-fill SL branches (including `NO_SL_SCALE`'s ADX gate, mocked
  via `dpm_engine.compute_adx`), and the Risk Governor sizing/gate integration.

## What to do

1. Write the test file using `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to
   a fake test-double (`get_tick`/`place_order`/`modify_order`/`get_account`), `_dpm_candles`
   set as needed per test.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed or modified — verified via the fake bridge's call logs.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

33 tests written in `tests/core/test_signal_resolution_characterization.py`. No `engine.py`
bugs found; several test-design corrections needed along the way (all in my own test code, not
the production code):

- `is_session_allowed`'s real risk-settings field names are `session_asia_enabled`/
  `session_london_enabled`/`session_ny_enabled` (no separate "overlap" toggle — overlap is
  derived from london OR ny being enabled).
- Confirmed `RG_MIN_TP1_RR` (1.00:1, pack 1's Risk Governor) is measured from the **live
  ask/bid**, not the zone midpoint — a signal whose TP1 clears the earlier, looser pre-trade
  filter (0.75:1, measured from zone mid) can still fail Risk Governor's own stricter check.
  Two RG-integration tests needed a wider TP1 to isolate the lot-sizing behavior under test
  from this (correct, working-as-designed) stricter gate.
- Risk Governor's lot sizing is doubly capped — by `risk_per_trade_pct` AND
  `max_risk_per_trade_pct` (both default low, 0.5%/1.0%) — so a naive test signal's normal
  10pt stop against the $1000 default balance rounds to a sub-0.01-lot rejection by default;
  needed to bump both settings meaningfully to get a valid RG-allowed lot size for the
  "RG overrides"/"RG yields to fixed lot" tests, while deliberately keeping a small stop's
  natural sub-0.01 rejection as the actual "RG blocks" test case.
- Simple arithmetic slip in my own test comment (mid − 10×1.5 = 2385, not 2375) for
  `NO_SL_SCALE`'s widened-SL branch — caught immediately by the failing assertion.

All 7 per-strategy pre-fill SL branches, the 3-tier strategy-resolution precedence, all 8
lot-sizing paths, and every gate (circuit breaker, session, R:R filter, price zone, spread,
channel pause) characterized and green against unmodified `engine.py`.
