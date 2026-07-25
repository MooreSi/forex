# Core: Open Trade From Signal Migration (back half)

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Thirteenth `core/engine.py` domain pack — the back half of `open_trade_from_signal`, completing
the split started in [core-signal-resolution-migration](../core-signal-resolution-migration/)
(pack 12, the front half). Same hard rule applies and is reconfirmed: **no real or demo MT5
order is ever placed or modified by this pack's code, its tests, or the agent directly.** All
bridge/EA interaction is through fakes; `bridge.place_order`, `bridge.modify_order`, and
`ea_bridge.EABridge.open_trade`/`update_trade` are never actually invoked against a live
account anywhere in this work.

## What we're building & why

Lines 1141-1393 of `open_trade_from_signal` — everything after strategy/lot_size/
stop_loss_to_use are resolved (pack 12's scope):

1. **Atomic signal claim** — a conditional `UPDATE ... WHERE status IN ('pending','active')`
   that only one concurrent caller can win (SQLite's writer lock), so the same signal can't be
   opened twice by two callers racing through the read-only checks at once.
2. **Call `open_trade`** (pack 11) with the resolved parameters; on any exception, restores the
   signal to `'pending'` so a transient failure (e.g. an MT5 reject) stays retryable, then
   re-raises.
3. **Six strategy-specific POST-fill overrides** (Conservative, Scalp Runner, Conservative
   Trial, GD VIP Runner, Adaptive Runner, Trail Stop) — each recomputes an exact SL (and, for
   the first two, TP1/TP2) from the trade's *actual fill price* (correcting for slippage vs.
   the pre-fill proxy values pack 12 computed), writes it to the DB, and calls
   `bridge.modify_order` to sync the SL to the live MT5 order. Conservative and Scalp Runner
   additionally call `ea_bridge.EABridge.update_trade` for EA-managed trades, since the EA's
   own in-memory TP tracking is captured once at open time and never refreshes on its own.
4. **Background open-commentary scheduling** — fire-and-forget, taken as an optional injected
   callable (default no-op), same pattern as pack 10's `schedule_profit_sync`/
   `background_close_commentary`.

## Target method slice (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `open_trade_from_signal` (back half — atomic claim + `open_trade` call + post-fill overrides) | 1141-1393 | `core_open_trade_from_signal.py` |

Calls `core_signal_resolution.resolve_open_trade_params` (pack 12) first, then
`core_open_trade.open_trade` (pack 11). Reuses `core_signal_resolution`'s `_gdvr_sl_dist`/
`_adaptive_sl_dist`/`_adaptive_final_tp_dist` and point-distance constants rather than
duplicating them a third time. The pre-fill entry-mid fallback values the original computed as
front-half locals (`_co_entry_mid` etc., only used when `result["entry_price"]` is somehow
falsy — dead in practice since `open_trade` always populates a real float) are recomputed
fresh from `sig["entry_low"]`/`sig["entry_high"]` here — same formula, same signal row,
behaviorally identical.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-open-trade-from-signal.md](010-characterize-open-trade-from-signal.md) | Characterization tests against current `engine.py` |
| [020-extract-open-trade-from-signal.md](020-extract-open-trade-from-signal.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Completes the split from pack 12; back half only | user, 2026-07-20 |
| This pack's scope | Atomic claim, `open_trade` call, the 6 post-fill override branches, background-commentary scheduling | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed or modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `open_manual_market_order`, `update_signal` — both still deferred, same risk class.
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
