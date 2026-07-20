# Core: Open Trade Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Eleventh `core/engine.py` domain pack — third in the trade-management cluster, after pack 9
(`partial_close_trade`) and pack 10 (`close_trade`/`_record_close`). Same hard rule applies and
is reconfirmed: **no real or demo MT5 order is ever placed by this pack's code, its tests, or
the agent directly.** All bridge/EA/sync interaction is through fakes or the modules' own
natural "unconfigured" defaults; `bridge.place_order` and `ea_bridge.EABridge.open_trade` are
never actually invoked against a live account anywhere in this work.

## What we're building & why

`open_trade` (lines 637-873) — the lowest-level trade-opening primitive every other opener
(`open_trade_from_signal`, `open_manual_market_order`, forwarded remote orders) eventually
calls. Given a fully-resolved direction/entry/SL/TP/lot size, it: checks the Local/Remote
standing-down gate, optionally forwards to a paired VPS node, checks the trading-pause flag,
the global circuit breaker, and the max-open-trades cap, then places the order — either via
the companion MQL5 EA (when enabled/healthy/portable for the strategy) or the Python MT5
bridge directly — and inserts the resulting `vantage_simulated_trades` row.

## Why this pack is smaller than it looks

`open_trade` is ~240 lines and touches more distinct subsystems than `close_trade` did (Local/
Remote sync forwarding, the EA bridge, the Python MT5 bridge, several gate checks), but unlike
`close_trade` it needs **no new state-carrier class**:

- `ea_bridge`, `sync.server`, `sync.client` are already accessed via module-level
  `get_instance()` singletons in the original code — the extracted version imports and calls
  them exactly the same way, and tests use `ea_bridge.set_instance(fake)` / `db_module.
  set_app_config("sync_remote_host", ...)` to exercise the non-default branches, matching how
  the original code itself is already structured to be overridable without any engine instance
  involved.
- `is_trading_paused` is already extracted (pack 1's `core_risk_governor.is_trading_paused`) —
  reused directly instead of `self.is_trading_paused`.
- The only genuine `self`-dependency is `self._bridge` (`get_fresh_tick`/`place_order`), taken
  as an explicit `bridge` parameter, same pattern as every prior pack.
- No cache/dict cross-call state is touched (unlike `close_trade`'s TP-cache invalidation) — a
  fresh trade being opened has nothing to invalidate.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `open_trade` | 637-873 | `core_open_trade.py` |

Also ports the two small EA-ladder lookup tables it reads (`_EA_LADDER_PCTS`/
`_EA_LADDER_BE_AT_POS`, and the `_CLIMBER_PCTS`/`_GDVR_PCTS` tables they're built from) —
static data, verbatim, no logic changes; these are also used elsewhere in `engine.py` (the
signal_climber/gd_vip_runner handlers) but that's out of scope here.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-open-trade.md](010-characterize-open-trade.md) | Characterization tests against current `engine.py` |
| [020-extract-open-trade.md](020-extract-open-trade.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 9-10's precedent inside the trade-management cluster; smallest of the three "open" methods first | user, 2026-07-20 |
| This pack's scope | `open_trade` only | this file |
| Order-placement boundary | Hard rule, reconfirmed: no real/demo MT5 order (Python bridge OR EA) ever placed by this work. Tests use fakes/natural defaults only. | user, 2026-07-20 |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `open_trade_from_signal` (~500 lines — resolves a raw signal into the parameters `open_trade`
  needs: strategy selection, SL/TP calculation, sizing) and `open_manual_market_order` — both
  callers of `open_trade`, not started.
- `update_signal` (modifies a live MT5 order — see pack 8's README).
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
