# Core TP Safety Net Migration

Extracts `SimulationEngine._tp_safety_net_sweep`, `_tp_safety_net_check_trade`,
`_compute_be_cost_pts` (core/engine.py) into a standalone module. Fourth pack
of the background-loops cluster in the "finish everything off" push,
continuing from `core-mt5-position-sync-migration`.

A periodic (every 180s, via the not-extracted `_tp_safety_net_loop` wrapper)
catch-all that protects any open trade whose breakeven-trigger TP was
genuinely touched (checked against real M1 candle highs/lows since open) but
the live per-tick strategy handler somehow never registered it -- moving SL
to breakeven-plus-estimated-round-trip-cost so a favourable move that was
missed doesn't give back as a full loss. Every branch traces back to a real
production incident documented in the original code's own comments (tickets
1556670216, 1543877939, 1543412796).

Key behaviors: skips BE Runner (broker-managed TP, nothing to protect) and
already-protected trades; skips EA-managed trades only while the EA instance
reports itself healthy (falls through to protect if the EA is absent or
unhealthy); resolves the correct breakeven-trigger TP per strategy (TP2 for
GD VIP Runner / Scalp Runner, which deliberately keep a wider SL until TP2 --
TP1 would be the wrong trigger); detects when the "protection window" has
already closed (price retraced past the computed breakeven+cost level before
this sweep got to it) and alerts without attempting an invalid stop move;
distinguishes a broker-side rejection (`modify_order` returning `{"success":
False}`, not an exception) from a real move, since only a successful move may
mark the trade protected. All alerts are cooldown-gated (30 min) per trade so
a persistently-failing case doesn't re-alert every 3-minute sweep forever.

`ea_bridge.get_instance()` is faked in tests -- it's real, external
infrastructure, same treatment as `sync.server`/`sync.client` throughout
prior packs.

See `PROGRESS.md` for task status.
