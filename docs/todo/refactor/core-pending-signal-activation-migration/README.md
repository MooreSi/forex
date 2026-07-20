# Core Pending Signal Activation Migration

Extracts `SimulationEngine._try_activate_pending_signals` (core/engine.py)
into a standalone module. Second pack of the background-loops cluster in the
"finish everything off" push, continuing from `core-profit-sync-migration`.

This is the zone-fill watcher referenced throughout several already-extracted
packs (ORB report's auto-execute, `/activate`, the standard Telegram signal
path) -- called every monitor-loop cycle, it activates any queued (`status=
'pending'`) signal once price re-enters its entry zone, with per-source
expiry windows (2 min default, 15 min for GD2, 60 min for ORB, 4 hours for
GD VIP Runner / Adaptive Runner), a post-failure backoff so a rejected
activation isn't retried every single cycle, pre-trade R:R/directional-cap
filtering (skipped for strategies that self-manage risk from their own
levels), a duplicate-open-trade guard, and a momentum-confirmation check
against the last completed M5 candle.

Calls the already-extracted `core_open_trade_from_signal.open_trade_from_signal`
(pack 13) and `core_risk_governor.check_pre_trade_filters`/
`price_in_entry_range` (already extracted) -- `open_trade_from_signal` is
mocked in this pack's tests, same treatment as `open_trade` throughout the
IME packs; its own real behavior was already characterized in its own
extraction pack.

`self._pending_activation_retry_after` (the per-signal backoff timestamp
dict) and `self._dpm_candles` are taken as explicit parameters, matching the
established pattern for instance state that isn't derivable from the
database (same as `scale_out_last_fail` in the scale-out handler pack).

See `PROGRESS.md` for task status.
