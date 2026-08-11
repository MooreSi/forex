# Core: Update Signal Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Fifteenth `core/engine.py` domain pack — `update_signal`, the last deferred piece of the
trade-management cluster (packs 9-14). Flagged as its own risk class back in pack 8's README
because it modifies a **live** MT5 order's SL/TP, not just places/closes one. Same hard rule
applies and is reconfirmed: **no real or demo MT5 order is ever modified by this pack's code,
its tests, or the agent directly.**

## What we're building & why

`update_signal` (lines 7496-7641) — edits a signal's fields (direction/entry zone/SL/TP1-8/
notes) and, if the signal has a linked **open** trade, propagates the relevant changes to it:

1. Updates `vantage_signals` with the allowed fields from the caller's `updates` dict.
2. If an open trade is linked and its strategy isn't one of the three that manage their own
   fixed levels post-fill (Conservative, Conservative Trial, Scalp Runner — these ignore
   follow-up signal edits by design, since they've already overridden SL/TP from the actual
   fill price), propagates SL/TP changes to `vantage_simulated_trades`.
3. For an MT5-backed trade, validates the new SL is on the correct side of the fill price
   before sending it (a stale/wrong-side SL is silently dropped, not sent to the broker), and
   only sends a broker-side TP for `STRATEGY_BE_RUNNER` (mirrors `open_trade`'s own mt5_tp
   resolution).
4. Skips the direct `bridge.modify_order` call when the companion MQL5 EA is actively managing
   the trade (its own on-tick logic is the sole source of truth for SL progression) — but
   **always** calls `ea_bridge.update_trade` for an EA-managed trade regardless, so the EA's
   own stale in-memory TP copy still gets refreshed.

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `update_signal` | 7496-7641 | `core_update_signal.py` |

Takes `bridge` explicitly instead of `self._bridge`. `ea_bridge` accessed the same
module-level-singleton way as packs 11/13.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-update-signal.md](010-characterize-update-signal.md) | Characterization tests against current `engine.py` |
| [020-extract-update-signal.md](020-extract-update-signal.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Closes out the trade-management cluster after packs 9-14 | user, 2026-07-20 |
| This pack's scope | `update_signal` only | this file |
| Order-modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing — everything left in `core/engine.py` after this
  pack closes out the trade-management cluster.
- Wiring the new function back into `engine.py`.
