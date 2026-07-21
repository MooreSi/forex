# Core Scan Messages: Auto-Execute Migration

Sub-pack D of `core-scan-messages-migration` (see its README for the full
scoping breakdown) -- the final piece of the entire `core/engine.py`
migration. Extracts the auto-execution flow embedded inline in
`SimulationEngine._scan_messages` (core/engine.py, lines 6984-7364) into a
standalone module.

**Real-money surface: highest in the whole migration series.** This block
places a real MT5 order via `open_trade` (already extracted,
independently characterized in `core-open-trade-migration` -- reused, not
re-derived) and, for Conservative/Scalp Runner, follows up with a
`modify_order` SL/TP sync and an EA `update_trade` call on a live ticket.
Every test here fakes `open_trade` and the bridge -- no real or demo order
is ever placed.

Gate order (first match wins): IME follow-up already matched (apply to the
existing instant trade instead of opening a new one) -> session gate ->
per-signal AI skip -> max open trades -> no live tick -> signal
validation (self-managed strategies validate only the entry zone shape;
Signal Climber/GD VIP Runner/Adaptive Runner and everything else validate
full R:R+TP geometry) -> zone-breach detection (price already broke
through the wrong side -> reject outright) -> pre-trade R:R/directional-cap
filter (skipped for self-managed strategies, which don't use the signal's
own TP geometry) -> lot sizing -> **gap-adjusted market entry** (GD2/Gold
Diggers VIP only, IME-on only: shifts all TP/SL levels by the price gap
and executes at market instead of queuing, when the gap is within the
channel's own cap) -> in-zone (execute now) vs out-of-zone (queue as
`pending`, the monitor loop's pending-signal watcher activates it later).

On a successful fill, Conservative/Scalp Runner overwrite the signal's own
SL/TP with exact fill-relative levels (their own fixed-point-from-fill
strategy) via a DB update, a `modify_order` broker sync, and (if
EA-managed) an `ea.update_trade` call. `open_trade` raising is handled by
error class: a "stood down" (centralized-generation mutual-exclusion)
error is expected and handled silently -- no alert, the other node
executes and alerts instead; a circuit-breaker error surfaces its own
message directly as the skip-reason; anything else gets a generic
"Auto-execution failed" skip-reason. Either way the signal reverts from
`active` back to `pending` so a later retry (manual or the pending-signal
watcher) can still pick it up.

The final Telegram alert (built regardless of whether execution happened,
covering both "executed" and every skip reason) is suppressed entirely
when `trade_result.get("executed_remotely")` is true -- the VPS that
actually placed a centrally-generated trade already sends its own
"Node: Remote" alert; this node sending a second, misleadingly
"Node: Local"-labeled one would be a duplicate.

`_price_in_entry_range` (a small pure static method) is ported verbatim.
`_check_pre_trade_filters`/`suggest_lot_size`/`_get_trading_balance`/
`get_open_trades`/`_find_and_apply_instant_followup` remain unextracted
small/already-extracted collaborators, taken as explicit injected
callables per the parent scoping doc's "no dedicated pack for thin/pure
helpers" decision.

See `PROGRESS.md` for task status.
