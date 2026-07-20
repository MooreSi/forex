# Core: Untracked MT5 Positions Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Sixth `core/engine.py` domain pack — closes out the item pack 3
([core-trade-reporting-migration](../core-trade-reporting-migration/)) explicitly deferred.

## What we're building & why

`get_untracked_mt5_positions` (line 1916) — returns live MT5 positions that have no matching
`vantage_simulated_trades` row (i.e. opened directly in MT5, not through the app). It's a
**read**: `self._bridge.get_positions()` over HTTP to the bridge, cross-referenced against
`core_trade_reporting.get_open_trades()` (pack 3). No order placement, no writes.

Deferred from pack 3 because it's `async` and bridge-dependent — a different, slightly
higher-risk shape than the three pure-DB-read functions there. Scoping it as its own tiny pack
now that a bridge test-double pattern is worth establishing cleanly.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `get_untracked_mt5_positions` | 1916-1935 | `core_untracked_positions.py` |

Takes `bridge` as an explicit parameter (anything exposing sync `is_configured() -> bool` and
async `get_positions() -> list[dict]`, matching `MT5BridgeClient`'s real shape) instead of
reading `self._bridge`. Calls `core_trade_reporting.get_open_trades()` (pack 3) directly instead
of `self.get_open_trades()`.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-untracked-positions.md](010-characterize-untracked-positions.md) | Characterization tests against current `engine.py` |
| [020-extract-untracked-positions.md](020-extract-untracked-positions.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-5's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | `get_untracked_mt5_positions` only, closing pack 3's deferral | this file |
| Bridge access | Explicit `bridge` parameter, not `self._bridge` — a fake bridge test-double is used in tests, no live MT5 connection is opened | this file |
| Real-money surface | None — read-only (`get_positions()` is an HTTP GET), no order placement | verified by reading the code |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in (same precedent as all prior packs) | precedent |

## Out of scope (explicitly, for this pack)

- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- Any other bridge methods (`startup`, order placement, etc.) — this pack only touches
  `is_configured()` and `get_positions()`.
- The 13 TP/SL strategy handlers, DPM's handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing — same deferral list as before.
- Wiring the new function back into `engine.py`.
