# Core MT5 Position Sync Migration

Extracts `SimulationEngine._sync_closed_mt5_positions` (core/engine.py) into
a standalone module. Third pack of the background-loops cluster in the
"finish everything off" push, continuing from
`core-pending-signal-activation-migration`.

The largest and most complex single function migrated so far in this push:
reconciles the app's locally-tracked open trades against MT5's real live
positions each monitor-loop cycle, handling four distinct scenarios --

  1. **Still open**: ticket present in `get_positions()` -- clears any
     miss-streak, no action.
  2. **Transiently missing**: ticket absent, but fewer than
     `MT5_SYNC_MISS_THRESHOLD` (2) consecutive misses -- not yet treated as
     closed, guards against a momentary bridge IPC hiccup falsely closing a
     genuinely-open trade.
  3. **Partial close**: MT5's deal history shows fewer lots closed than the
     app is tracking as remaining -- records a partial close (reusing the
     already-extracted `partial_close_trade`) and, if the continuing
     position reappears under a new ticket (hedge-account behavior),
     reassigns `mt5_ticket` to follow it.
  4. **Full close**: infers the close reason (SL / TP / plain MT5 close) from
     the closing deal's comment text, then finalizes via the already-
     extracted `record_close` + `sync_profit`/`schedule_profit_sync`
     (`core_profit_sync.py`, pack 34).

A second, independent pass then imports any live MT5 position with no
matching local trade row -- but **only reachable when at least one locally-
tracked open trade already exists**: the function returns immediately, before
ever calling `get_positions()`, if the app's own open-trades query comes back
empty. A genuinely fresh install (or a DB that's lost all its open-trade rows)
with real MT5 positions already open would never have them auto-discovered by
this loop alone -- confirmed via a direct trace, not just reading the code,
and documented as a real, non-obvious characterization finding, not a bug to
fix here.

Trades linked to `vantage_ladder_legs` rows (Adaptive Runner ladder anchors)
are excluded from both the close-detection and the reimport passes -- their
own ticket is only leg 1, and the code comments explain in detail why
treating it as the whole position previously caused real production
incidents.

See `PROGRESS.md` for task status.
