# Core Max TP Hit Migration

Extracts `SimulationEngine._max_tp_checker_loop`'s per-cycle sweep body and
`SimulationEngine._backfill_max_tp_hit_corrected` (core/engine.py) into a
standalone module, plus the pure module-level helper `_tp_level_from_extreme`
(engine.py:116-132). Fifth pack of the background-loops cluster in the
"finish everything off" push, continuing from `core-tp-safety-net-migration`.

`_max_tp_checker_loop` runs every 5 minutes (after a 90s startup delay, both
left as the thin loop shell in `engine.py`, same split precedent as
`_tp_safety_net_loop`/`_tp_safety_net_sweep`): finds closed trades whose
30-minute settling window has elapsed with no `max_tp_hit` computed yet,
fetches M1 candles for the trade's own `open_time`->`close_time` window, and
records the highest TP level (TP1..TP8) the price extreme reached in the
trade's favourable direction -- preferring the original Telegram signal's TP
ladder (`sig_tp1..sig_tp8`) over the strategy's own possibly-overridden TPs,
so the column reflects how far price ran relative to what was actually
signalled. Falls back to `"none"` directly (no candle fetch) when
`open_time`/`close_time`/`direction` is missing. Best-effort pushes the
result to the consolidated ledger via `sync.ledger.push_trade_closed` after
each save.

`_backfill_max_tp_hit_corrected` is a genuine one-off task (own 120s startup
delay, no `while` wrapper) added 2026-07-18 to correct every already-computed
`max_tp_hit` value: the loop's fetch window used to extend 30 minutes past
`close_time`, so a value could reflect price action from after the trade had
already closed (ticket 1615526315). Recomputes each row the same way and only
writes back + re-pushes to the ledger when the corrected value actually
differs from the stored one -- idempotent, safe to leave running at every
startup.

Both `db_module.get_trades_pending_max_tp`/`get_trades_with_max_tp_set`
already filter to `close_time > 0`, so the "missing close_time" defensive
branch in both loops is unreachable via real data; only "missing/zero
`open_time`" and "missing `direction`" are reachable in practice (both
columns are `NOT NULL` but a `0.0`/`""` placeholder value satisfies the
constraint).

See `PROGRESS.md` for task status.
