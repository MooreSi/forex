# Core: Signal Resolution Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Twelfth `core/engine.py` domain pack — first half of `open_trade_from_signal`
(lines 890-1393, ~500 lines total), the largest single method in the file. Split into two
packs given the size; read this file's "Why split in two" before assuming the whole method is
in scope.

## What we're building & why

The **front half** of `open_trade_from_signal`: everything from the signal fetch through
resolving the final `strategy`/`lot_size`/`stop_loss_to_use` that get handed to `open_trade`
(pack 11) — lines 894-1139. This covers:

- Signal fetch + status validation.
- Global circuit breaker, Trading Markets session gate.
- Strategy resolution (channel override > auto-Claude rec > global Active Strategy).
- Pre-trade R:R/directional-cap filter (skipped for the 6 strategies that manage their own
  levels).
- Live-price zone check + spread guard.
- Channel scorecard pause check + adaptive lot-size multiplier.
- Lot sizing (risk-derived, fixed override, channel multiplier, strategy-fixed-lot, signal-age
  decay).
- Per-strategy SL override for the 7 strategies that compute their own pre-fill SL (Trend
  Ratchet's ADX gate, Conservative/Scalp Runner/Conservative Trial/Trail Stop/GD VIP
  Runner/Adaptive Runner's fixed-point or widened-SL math).
- Tier 1 Risk Governor sizing/hard-gate check (when enabled) — authoritative over the
  risk-derived lot size.

**No MT5 order is placed or modified anywhere in this pack's scope** — it's pure computation
and DB reads/writes (the DB writes are all to `vantage_signals`/channel-scorecard tables, not
`vantage_simulated_trades`). The one bridge touch is `bridge.get_tick()`/`_get_trading_balance()`
(pack 10, reused) — both reads.

## Why split in two

`open_trade_from_signal` is too large and too risky to characterize/extract as one unit:

1. **Size**: ~500 lines total; this front half alone is ~245 lines with 7 independent
   strategy-specific branches, each needing its own characterization tests.
2. **Risk class boundary**: the **back half** (lines 1141-1393 — the atomic signal-claim, the
   call into `open_trade`, and 6 strategy-specific *post-fill* SL/TP override branches) calls
   `bridge.modify_order` directly against the just-opened live position. That's the same risk
   class as `update_signal` (deferred after pack 8 for exactly this reason) — modifying a live
   order, not just placing one. Splitting lets this pack stay in the "pure computation, no
   order mutation" class, with the back half scoped as its own pack (13) with that risk called
   out explicitly.

The split point (`open_trade`'s "Atomic claim" section) is a natural boundary already marked by
a comment in the original code.

## Target method slice (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `open_trade_from_signal` (front half only — gates + strategy resolution + pre-fill sizing) | 894-1139 | `core_signal_resolution.py` |

Reuses `core_risk_governor.check_pre_trade_filters`/`price_in_entry_range`/`rg_size_and_check`/
`is_trading_paused` (pack 1), `core_fees_sizing.suggest_lot_size` (pack 1),
`core_close_trade.get_trading_balance` (pack 10) instead of the `self.*` equivalents. Ports the
`_gdvr_sl_dist`/`_adaptive_sl_dist`/`_adaptive_final_tp_dist` helper functions and the
per-strategy point-distance constants (`_CONSERVATIVE_SL_PT` etc.) verbatim — these are also
used by the (deferred) back half and by the (deferred) post-fill override branches themselves,
so they'll be imported from here rather than duplicated again in pack 13.

`self._dpm_candles` (an instance attribute refreshed by the, also deferred, `_monitor_loop`) is
taken as an explicit `dpm_candles: Optional[list]` parameter — not derivable from the database,
same treatment as pack 4/5's cache parameters.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-signal-resolution.md](010-characterize-signal-resolution.md) | Characterization tests against current `engine.py` |
| [020-extract-signal-resolution.md](020-extract-signal-resolution.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | `open_trade_from_signal` split in two at its own "Atomic claim" boundary; this pack is the pure-computation front half | this file, given the size/risk-class jump |
| This pack's scope | Signal fetch/validate through strategy+lot_size+stop_loss_to_use resolution (lines 894-1139) only | this file |
| Back half (pack 13, not started) | Atomic claim + `open_trade` call + 6 post-fill `bridge.modify_order` override branches — same risk class as `update_signal` | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed or modified by this work. This pack touches the bridge for reads only (`get_tick`/`get_account` via `get_trading_balance`). | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The back half of `open_trade_from_signal` (atomic claim, `open_trade` call, post-fill
  `modify_order` overrides) — pack 13.
- `open_manual_market_order`, `update_signal` (both modify/place live orders).
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
