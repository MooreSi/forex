# 010 — Characterize IME follow-up flow

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order's SL/TP via `bridge.modify_order`
-- tested against a fake bridge only. `update_signal` (called for the
signal-linked path) is the already-extracted, real propagation function --
exercised for real here (DB-only + fake bridge), not mocked, since it's
DB/bridge-only and cheap to run directly.

## Decision

Same fake-bridge approach as prior packs. Every branch's exact numeric output
was traced against unmodified `engine.py` via throwaway scripts first, given
how the TP-validity/auto-spacing check and the BE-Runner-specific safe-TP
fallback interact.

## Tests first (TDD)

- `tests/core/test_instant_followup_characterization.py`:
  - `_apply_followup_to_instant_trade`:
    - Self-managed strategy (Conservative), channel override matches (or is
      unset) -> acknowledged only, trade's SL/TPs untouched, `tg_signals` row
      marked `followup_applied`.
    - Self-managed strategy, channel override has since diverged -> the
      trade's `strategy` column is corrected in place and the signal's
      levels ARE applied (falls through rather than returning early).
    - Non-self-managed strategy, 2+ of the signal's TPs land in the
      profitable direction from the actual fill -> applied exactly as
      parsed via `update_signal`.
    - Fewer than 2 valid TPs -> six standard TP levels auto-spaced from the
      actual fill price instead (overriding the signal's own TP1 onward),
      TP7/TP8 cleared, a "TPs Adjusted" Telegram alert sent.
    - No linked signal record (falls back to a direct DB update): SL/TPs
      written directly, `bridge.modify_order` called with the parsed SL.
    - No linked signal record, strategy is BE Runner: `modify_order`'s `tp`
      argument is the highest-tier TP defined (scanning TP8 down to TP1)
      that's still in the profitable direction from the fill -- not
      necessarily TP1.
    - No linked signal record, any other strategy: `modify_order`'s `tp`
      argument is always `None` (only BE Runner gets a safe-TP fallback).
  - `_find_and_apply_instant_followup`:
    - No open instant trade for the channel -> returns `False`, nothing
      applied.
    - An open trade exists but its direction doesn't match the follow-up ->
      returns `False`.
    - A matching open trade exists -> applies the follow-up and returns
      `True`.
  - `_ime_timeout_watchdog`:
    - A trade younger than the 3-minute timeout -> untouched.
    - A self-managing-strategy trade past the timeout -> skipped (logged,
      not touched) rather than overwritten with generic auto-assigned levels.
    - A trade past the timeout, price hasn't yet cleared the auto-assigned
      TP1 -> six TP levels assigned, SL left at its current (provisional)
      value -- but `bridge.modify_order` is still called unconditionally
      with that unchanged SL whenever an `mt5_ticket` exists (no
      `should_update`-style gate here, unlike the TP/SL strategy handlers).
    - A trade past the timeout, price has already cleared the auto-assigned
      TP1 -> SL additionally moves to breakeven (entry price),
      `sl_moved_to_be` set.

## What to do

1. Write the test file using a fake bridge (`modify_order`), calling the
   methods via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

13 tests written in `tests/core/test_instant_followup_characterization.py`,
all green on the first run against unmodified `engine.py` -- every branch
was pre-traced via throwaway scripts, given how the TP-validity/auto-spacing
check and the BE-Runner-specific safe-TP fallback interact. No `engine.py`
bugs found.

One genuine, non-obvious behavior confirmed via a dedicated test:
`_ime_timeout_watchdog` calls `bridge.modify_order` *unconditionally*
whenever `mt5_ticket` is set, even when the computed SL is identical to the
trade's current SL (the "TP1 not yet cleared" case) -- unlike the TP/SL
strategy handler family, which consistently gates broker syncs behind a
`should_update`-style comparison before calling `modify_order`. Preserved
verbatim, not "fixed" -- a redundant-but-harmless broker call every watchdog
cycle for any trade still waiting on its follow-up.

`vantage_simulated_trades.signal_id` is `NOT NULL` with a foreign key to
`vantage_signals.signal_id` -- the "no linked signal" fallback path is
exercised by inserting both rows with `signal_id=""` (an empty string, which
satisfies the schema constraints but is still falsy in Python's
`if signal_id:` check the original code uses), not a true SQL NULL.
