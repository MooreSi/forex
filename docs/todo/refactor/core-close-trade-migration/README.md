# Core: Close Trade Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Tenth `core/engine.py` domain pack — second in the trade-management cluster, after pack 9's
`partial_close_trade`. Same hard rule applies and is reconfirmed: **no real or demo MT5 order
is ever placed, closed, or modified by this pack's code, its tests, or the agent directly.**
All bridge interaction is through fakes; `bridge.close_position` is never actually invoked
against a live account anywhere in this work.

## What we're building & why

`close_trade`, `_record_close`, `_close_all_ladder_legs`, `_get_trading_balance` (lines
875-1832, non-contiguous) — the full accounting path for closing a trade: calls
`bridge.close_position` for the real broker-side close, then records P&L, balance, peak
watermark, and cascades into several other subsystems (ledger sync, DPM finalization, Risk
Governor halt check, circuit breaker).

| Current method | Lines | New home |
|---|---|---|
| `close_trade` | 1626-1675 | `core_close_trade.py` |
| `_record_close` | 1677-1831 | `core_close_trade.py` |
| `_close_all_ladder_legs` | 1549-1624 | `core_close_trade.py` |
| `_get_trading_balance` | 875-888 | `core_close_trade.py` |

## Why this pack is a bigger jump than pack 9

Unlike `partial_close_trade`, this cluster:
1. **Calls `bridge.close_position` directly** — the actual MT5 order-close call. Tested only
   against a fake bridge; never invoked for real.
2. **Reuses three already-extracted modules** instead of re-deriving their logic:
   `core_fees_sizing.pnl()` (pack 1), `core_risk_governor.rg_apply_halts_on_close()` (pack 1),
   `core_dpm_bookkeeping.finalize_dpm_record()` (pack 4).
3. **Touches instance state belonging to still-deferred subsystems** — `self._tp_cache` (pack
   5's `TPCache`, reused), `self._scale_out_last_fail` and `self._tp_safety_net_last_alert`
   (dicts owned by the not-yet-extracted scale-out handler and TP Safety Net loop —
   `close_trade`/`_record_close` only ever *pop* entries from them on close, never populate
   them, so they're safe to take as plain externally-owned dicts here without extracting
   those subsystems).
4. **Fires two long-running background tasks** (`_schedule_profit_sync` — retries for up to 30
   minutes; `_background_close_commentary` — AI/Telegram notification) via
   `asyncio.create_task(...)`, never awaited. Both are far larger, separate pieces of work;
   taken here as optional injected async callables (default: no-op) so `close_trade`'s own
   return value and side effects are fully testable without needing to build either subsystem.
5. **Increments `self._profit_sound_seq`** (a UI sound-notification counter) — taken as an
   optional `on_profit()` callback instead of mutating counter state directly.

To keep the resulting function signatures manageable, these collaborators are bundled into one
small `CloseTradeContext` container (mirrors pack 4/5's `DPMCache`/`TPCache` precedent — a
purpose-built carrier for cross-call state and injected collaborators, not a mixin, not hidden
global state).

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-close-trade.md](010-characterize-close-trade.md) | Characterization tests against current `engine.py` |
| [020-extract-close-trade.md](020-extract-close-trade.md) | Extract into standalone, tested functions |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing pack 9's precedent inside the trade-management cluster | user, 2026-07-20 |
| This pack's scope | `close_trade`/`_record_close`/`_close_all_ladder_legs`/`_get_trading_balance` | this file |
| Order-placement boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use a fake bridge only. | user, 2026-07-20 |
| Deferred subsystem state | `scale_out_last_fail`/`tp_safety_net_last_alert` taken as plain externally-owned dicts (only ever popped-from here); `_schedule_profit_sync`/`_background_close_commentary` taken as optional injected callables (default no-op) | this file, to avoid extracting subsystems out of scope |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `open_trade`, `open_trade_from_signal`, `open_manual_market_order` — real order placement,
  not started.
- `update_signal` (modifies a live MT5 order — see pack 8's README).
- `_sync_profit`/`_schedule_profit_sync`'s internals, `_background_close_commentary`'s
  internals — both taken as injected no-op-by-default callables, not extracted here.
- The 13 TP/SL strategy handlers (including the scale-out handler that owns
  `scale_out_last_fail`), DPM's own handler, the TP Safety Net loop (owns
  `tp_safety_net_last_alert`), IME, the ~25 Telegram bot commands, ORB, other background sync
  loops, AI fallback parsing.
- Wiring the new functions back into `engine.py`.
