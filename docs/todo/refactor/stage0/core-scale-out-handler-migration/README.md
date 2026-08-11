# Core: Scale Out Handler Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Seventeenth `core/engine.py` domain pack — second in the TP/SL strategy-handler cluster, after
pack 16's `_handle_orb_fixed`. Same hard rule applies and is reconfirmed: **no real or demo
MT5 order is ever placed, closed, or modified by this pack's code, its tests, or the agent
directly.**

## What we're building & why

`_handle_scale_out` (lines 2177-2247) — the default TP/SL strategy (`STRATEGY_SCALE_OUT`,
the global fallback whenever no other strategy is configured). On each TP hit: closes a tiered
percentage of the position (40/30/20/10 for TP1-4, 100% of whatever remains for the last
defined TP or any TP5+), retries a failed broker-side partial close no more than once per 30s
per (trade, TP level), and moves SL to breakeven the first time TP1 is hit.

## Why `_close_full_after_tps` is NOT in this pack

`_handle_scale_out` fires `asyncio.create_task(self._close_full_after_tps(...))` — fire-and-
forget, never awaited — when a partial close empties the position. `_close_full_after_tps`
itself is a large, separate method (residual-position verification against the live bridge,
profit sync, a full Telegram close notification) that deserves its own scoping pass. Taken
here as an optional injected async callable (default no-op), same pattern as pack 10's
`schedule_profit_sync`/`background_close_commentary` and pack 13's
`background_open_commentary`.

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_scale_out` | 2177-2247 | `core_handle_scale_out.py` |

Takes `bridge`, a `TPCache` (pack 5), and `scale_out_last_fail: dict` (the per-(trade_id,
tp_num) retry-cooldown tracker — externally owned, same treatment as pack 10's `CloseTradeContext`
dicts) explicitly. Reuses `core_tp_trigger_tracking.check_tp_hits`/`get_remaining_lots` (pack
5), `core_partial_close.partial_close_trade` (pack 9). `close_full_after_tps` taken as an
optional injected callable.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-scale-out.md](010-characterize-handle-scale-out.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-scale-out.md](020-extract-handle-scale-out.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing pack 16's precedent in the TP/SL handler cluster | user, 2026-07-20 |
| This pack's scope | `_handle_scale_out` only; `_close_full_after_tps` deferred as an injected callable | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `_close_full_after_tps` (deferred, its own future pack).
- `_handle_be_runner` — falls back to Scale Out when ADX indicates a ranging market; will reuse
  this pack's extracted function once it's its own pack.
- The other 11 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands,
  ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
