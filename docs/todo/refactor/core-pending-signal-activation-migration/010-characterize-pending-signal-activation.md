# 010 — Characterize pending signal activation

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** places a genuine MT5 market order via
`open_trade_from_signal` (already extracted, pack 13) -- mocked in every
test here, same treatment as `open_trade` throughout the IME packs.

## Decision

`open_trade_from_signal`/`get_open_trades` mocked. Every branch's exact
behavior was traced against unmodified `engine.py` via throwaway scripts
first, given how many gates interact (expiry, backoff, zone, max-trades,
pre-trade filters, duplicate guard, momentum).

## Tests first (TDD)

- `tests/core/test_pending_signal_activation_characterization.py`:
  - No pending signals -> returns `False` immediately.
  - Expired signal (default 120s window) -> marked `expired`, its backoff
    entry cleared, no activation attempt; an ORB-sourced expiry additionally
    sends a "reload zone not retested" alert.
  - Per-source expiry overrides: GD VIP Runner / Adaptive Runner get 4 hours,
    GD2-sourced signals get 15 minutes, ORB-sourced signals get 60 minutes,
    everything else gets the 120-second default -- verified by NOT expiring
    a 200-second-old GD VIP Runner signal that would expire under the
    default window.
  - Active backoff (from a prior failed attempt) -> skipped entirely, no
    zone/filter checks even run.
  - Price outside the entry zone -> skipped, `open_trade_from_signal` never
    called.
  - `max_open_trades` already reached -> the loop `break`s (not `continue`s)
    -- no further pending signals are processed that cycle either.
  - Pre-trade R:R filter blocks a low-R:R signal for a normal strategy ->
    skipped.
  - A self-managing strategy (Conservative, Conservative Trial, Signal
    Climber, GD VIP Runner, Adaptive Runner) bypasses the pre-trade filter
    entirely, even for a signal that would otherwise fail it.
  - An existing open/pending trade already linked to the signal -> marks the
    signal `activated` directly and skips, no duplicate `open_trade_from_signal`
    call.
  - Momentum mismatch (last M5 candle direction opposes the signal
    direction) -> skipped; only checked when candle data is available.
  - Momentum match -> proceeds to activation.
  - Successful activation -> calls `open_trade_from_signal` with
    `age_lot_mult=1.0`, flips the linked `vantage_tg_signals` row to
    `activated`, clears the signal's backoff entry.
  - A failed activation (any exception) sets a ~20-second backoff for that
    signal regardless of the exception's message.
  - Return value is `True` whenever any signal was pending at the start of
    the cycle, regardless of what happened to each one individually.

## What to do

1. Write the test file using mocked `get_open_trades`/`open_trade_from_signal`,
   calling `SimulationEngine._try_activate_pending_signals` via
   `SimulationEngine.__new__(SimulationEngine)` with
   `_pending_activation_retry_after = {}`, `_dpm_candles = []`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — `open_trade_from_signal`
  is mocked in every test, never given a real bridge to act through.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

13 tests written in
`tests/core/test_pending_signal_activation_characterization.py`, all green
on the first run against unmodified `engine.py` -- every gate (expiry,
backoff, zone, max-trades, pre-trade filters, duplicate guard, momentum)
was pre-traced via throwaway scripts given how many interact. No `engine.py`
bugs found.

Confirmed the `max_open_trades` gate `break`s the whole loop rather than
`continue`ing past just the current signal -- once the cap is hit, no later
pending signal in the same cycle gets a chance either, even if an earlier
one in iteration order was the one that filled it. Also confirmed the
duplicate-open-trade guard is the ONE place in this function that writes
`vantage_signals.status` directly (to `'activated'`) -- the normal success
path only flips the linked `vantage_tg_signals` row; `vantage_signals`'
own status transition happens inside the (mocked, separately-characterized)
`open_trade_from_signal`.
