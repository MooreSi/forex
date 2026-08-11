# 010 — Characterize MT5 position sync

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** never places, closes, or modifies a live MT5 order
itself (it only reads `get_positions`/`get_deal_history`/`get_position_history`
and writes to the DB via already-extracted, already-characterized helpers:
`partial_close_trade`, `record_close`, `sync_profit`, `schedule_profit_sync`,
all mocked in this pack's tests).

## Decision

Same fake-bridge approach as prior packs. `telegram_alerts.fmt_trade_close`
is mocked (not just `send_message`) in full-close tests -- it's called
eagerly (before `asyncio.create_task` wraps `send_message`), so leaving it
real requires fully-realistic `closed_row`/`account` dict shapes for no
characterization value; mocking it isolates this pack's own branching logic
from that formatter's own concerns. Every branch's exact behavior was
traced against unmodified `engine.py` via throwaway scripts first, given
the number of interacting paths (miss-streak debouncing, partial-close
ticket reassignment, reason inference, untracked-position import).

## Tests first (TDD)

- `tests/core/test_mt5_position_sync_characterization.py`:
  - Bridge not configured -> returns immediately, no DB reads at all.
  - No locally-tracked open trades -> returns after the fetch; **critically,
    this also skips the entire untracked-position-import pass** -- a live
    MT5 position with no local trade row is never discovered by this
    function alone unless at least one other trade is already tracked.
  - Ticket still present in `get_positions()` -> miss-streak cleared, no
    other action.
  - `get_positions()` returns empty AND the bridge reports disconnected ->
    the whole sync is skipped (ambiguous signal, not treated as "all
    closed").
  - Miss-streak below `MT5_SYNC_MISS_THRESHOLD` (2) -> not yet treated as
    closed, streak incremented.
  - Miss-streak reaches the threshold, no deal history at all -> full close
    using the live tick as a price fallback, reason defaults to
    `"MT5_close"`.
  - Full close: closing deal's comment mentions "sl" -> reason inferred as
    `"SL"`, the real close price taken from that deal.
  - Partial close detected (closed deal volume less than tracked remaining
    lots): calls `partial_close_trade`, does NOT call `record_close`,
    clears the miss-streak (trade stays open) -- and the reason string
    passed to `partial_close_trade` is `f"MT5_{reason}"` where `reason`
    itself can already be `"MT5_sync_TP"`, producing a literal
    `"MT5_MT5_sync_TP"` double-prefixed string. Preserved verbatim, not "fixed".
  - Partial close where the continuing position reappears under a different
    ticket at the expected remaining volume -> `mt5_ticket` is reassigned to
    follow it.
  - A trade linked to `vantage_ladder_legs` rows is excluded from the
    close-detection pass entirely -- its own (anchor-leg) ticket going
    missing from `get_positions()` never triggers any action.
  - Untracked-position import (with at least one other tracked trade
    present so the pass is reachable): a live position with no matching
    local ticket is imported as a new `open` trade with `signal_id=
    'MT5_DIRECT'` (via an idempotent sentinel signal row),
    `tg_source='MT5_imported'`, and the current default strategy.
  - A ticket already known via `vantage_ladder_legs` (not
    `vantage_simulated_trades` directly) is correctly excluded from
    re-import.

## What to do

1. Write the test file using a fake bridge (`is_configured`/`get_positions`/
   `get_health`/`get_deal_history`/`get_position_history`/`get_account`/
   `get_tick`), calling the method via
   `SimulationEngine.__new__(SimulationEngine)` with
   `_mt5_sync_missing_streak = {}`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — this function
  never calls a bridge order-mutation method at all.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers
  from prior packs.

## Notes

12 tests written in `tests/core/test_mt5_position_sync_characterization.py`,
all green on the first run against unmodified `engine.py` -- the most
extensively pre-traced pack in this whole migration series, given this
function's complexity (four distinct reconciliation paths plus a separate
import pass). No `engine.py` bugs found; two genuine, non-obvious findings,
both confirmed via direct throwaway-script traces rather than just reading
the code:

1. **The untracked-position-import pass is unreachable with zero locally-
   tracked open trades.** The function's very first substantive step is
   `open_trades = await ...; if not open_trades: return` -- so a live MT5
   position with no matching local row is never discovered by this loop
   alone unless at least one OTHER trade is already tracked in the DB. A
   fresh install (or any DB that lost its open-trade rows) sitting on real
   MT5 positions would silently never re-adopt them via this path.
2. **Double-prefixed partial-close reason string.** When a partial close's
   inferred `reason` is already `"MT5_sync_TP"` (from a "tp"/"take" comment
   match), the call to `partial_close_trade` uses `f"MT5_{reason}"`,
   producing the literal string `"MT5_MT5_sync_TP"` stored in
   `vantage_partial_closes.reason`. Preserved verbatim, not "fixed" -- this
   pack's job is characterization, not correction.

Also confirmed: trades linked to `vantage_ladder_legs` are excluded from
BOTH the close-detection query AND the untracked-import pass (via a
`UNION` of known tickets from both tables), so a ladder anchor's leg-1
ticket going missing from `get_positions()` never falsely triggers a close,
and a ladder leg's own ticket never gets re-imported as a phantom duplicate
trade.
