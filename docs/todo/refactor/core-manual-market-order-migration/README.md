# Core: Manual Market Order Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Fourteenth `core/engine.py` domain pack — `open_manual_market_order`, the manual-entry
counterpart to `open_trade_from_signal` (packs 12-13). Same hard rule applies and is
reconfirmed: **no real or demo MT5 order is ever placed by this pack's code, its tests, or the
agent directly.**

## What we're building & why

`open_manual_market_order` (lines 1395-1547) — places an immediate market order from the UI
(the dashboard's Market Order button, and the ORB/IVB Report tab's Execute Trade button)
without a pre-existing signal. Meaningfully smaller and simpler than `open_trade_from_signal`:
no atomic-claim race to guard (it creates its own fresh signal record every call, so there's
nothing to double-claim), no strategy-specific post-fill overrides, no EA-specific branching
beyond what `open_trade` (pack 11) already does internally.

Sequence: validate direction → fetch a fresh tick → resolve SL (explicit price with a sanity
check against implausible values, or DPM's ATR-based auto-SL, or reject if neither is
available) → resolve lot size (explicit, strategy-fixed, or risk-based) → create a backing
signal row (so the trade's foreign key resolves) → call `open_trade` → send a Telegram
notification and schedule background commentary (both fire-and-forget).

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `open_manual_market_order` | 1395-1547 | `core_manual_market_order.py` |

Takes `bridge` explicitly instead of `self._bridge`/`self.get_fresh_tick()`/`self.get_candles()`.
Reuses `core_fees_sizing.suggest_lot_size` (pack 1), `core_close_trade.get_trading_balance`
(pack 10), `core_open_trade.open_trade` (pack 11). `background_open_commentary` taken as an
optional injected callable, same pattern as pack 13.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-manual-market-order.md](010-characterize-manual-market-order.md) | Characterization tests against current `engine.py` |
| [020-extract-manual-market-order.md](020-extract-manual-market-order.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Next in the trade-management cluster after packs 9-13 | user, 2026-07-20 |
| This pack's scope | `open_manual_market_order` only | this file |
| Order-placement boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `update_signal` (modifies a live order — see pack 8's README) — the last deferred piece of
  the trade-management cluster after this pack.
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB
  report generation itself, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
