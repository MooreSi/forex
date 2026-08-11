# Core Monitor Loop Migration

Extracts the four genuinely-computational pieces embedded inline in
`SimulationEngine._monitor_loop` (core/engine.py, the master per-tick
dispatcher, 267 lines) into a standalone module. Ninth and final pack of
the background-loops cluster in the "finish everything off" push,
continuing from `core-bridge-watchdog-migration`.

`_monitor_loop` itself is intentionally **not** an extraction target as a
whole -- most of its bulk is pure dispatch: a per-trade strategy if/elif
routing table calling into the 13 already-extracted TP/SL handlers, plus
delegation to `_try_activate_pending_signals`/`_ime_timeout_watchdog`/
`_sync_closed_mt5_positions`/`_profit_sweep`/`_run_dpm_calibration` (all
already extracted in earlier packs) gated by simple cycle counters and an
adaptive sleep duration. That's the same "intended permanent thin
orchestration layer, not technical debt" judgment applied throughout this
whole migration series (most recently `_handle_bot_command`'s own routing
dict in the bot-commands cluster) -- reusing already-tested collaborators
through a stable dispatch shape isn't debt to pay down.

Four pieces inside it are genuine, previously-untested computation,
though, and get the full treatment:

1. **`check_sl`** (was `SimulationEngine._check_sl`) -- tiny pure helper,
   BUY/SELL stop-loss crossing detection. Ported verbatim.
2. **`reconcile_sl_hit`** -- when `check_sl` fires, this reconciles the
   local `remaining_lots` against MT5's own live position volume before
   trusting the crossing: if the position is still fully open at the
   broker (SL hasn't fired there yet), defer to next cycle rather than
   double-closing; if the broker already partially closed it, record a
   matching local partial close (`MT5_<reason>`); only a genuinely-gone
   ticket (or a bridge that's unconfigured/unreachable) triggers a full
   local close. Reuses the already-extracted
   `core_partial_close.partial_close_trade` and
   `core_close_trade.record_close`.
3. **`check_profit_close_target`** -- cumulative-P&L (realised partials +
   unrealised open) threshold check against the `profit_close_usd` risk
   setting; closes via MT5 when a ticket exists (falling back to the
   current tick price if the broker rejects or the call raises), then via
   the same `core_close_trade.record_close`.
4. **`reclaim_ea_managed_trade`** -- for EA-managed trades, checks the EA
   bridge's health and reclaims management back to Python (DB update +
   Telegram alert) the moment it goes silent, so a trade is never left
   with no one actively watching it.

All four take `bridge`/`ctx` (a `core_close_trade.CloseTradeContext`)
explicitly rather than `self`, same convention as every extraction in this
series. No new order-placing logic is introduced -- `reconcile_sl_hit` and
`check_profit_close_target` call the same real close/partial-close paths
the original code called.

See `PROGRESS.md` for task status.
