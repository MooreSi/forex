# Core: MT5 Deal History Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Eighth `core/engine.py` domain pack — first pack in the "needs a scoping call" bucket flagged
at the end of pack 7. Read [core-fees-risk-governor-migration](../core-fees-risk-governor-migration/)
first for the base pattern (same shape: `db_module.db()` is thread-local/re-entrant, no
parallel repo).

## What we're building & why

This pack covers three methods that all read (and in one case write) MT5 **deal history** —
distinct from every prior pack because they call `self._bridge.get_deal_history()` /
`get_account()` / `get_positions()`, real HTTP reads against the live bridge (never writes to
MT5, never places or modifies an order):

| Current method | Lines | New home | Shape |
|---|---|---|---|
| `get_total_deposits` | 7764-7794 | `core_total_deposits.py` | Read + 1hr app_config cache |
| `compute_mt5_performance` | 7643-7762 | `core_mt5_performance.py` | Read, aggregate into performance stats (reuses module-private `_apply_fee`/`_platform_fee_rate` helpers, ported alongside it) |
| `import_mt5_history` | 7390-7472 | `core_mt5_import.py` | Read MT5 deals, **write** `vantage_signals`/`vantage_simulated_trades`/balance for any closed position missing from the local DB (backfill only — never touches MT5 itself) |

All three take `bridge` as an explicit parameter instead of `self._bridge`, same pattern as
pack 6. `import_mt5_history` also calls `self.pnl(...)` — replaced with pack 1's
`core_fees_sizing.pnl()`.

## Why `update_signal` is NOT in this pack

`update_signal` (line 7496) was flagged in the same "needs a scoping call" bucket at the end of
pack 7, but closer reading shows it calls `self._bridge.modify_order(ticket, sl=.., tp=..)` and
(for EA-managed trades) `ea_bridge.get_instance().update_trade(...)` — both **modify a live MT5
position's SL/TP**, not just read history. That puts it in the same risk class as the 13 TP/SL
strategy handlers (which also call `modify_order`), not this pack's read/backfill-only scope.
Deferred to a future pack alongside those handlers, pending explicit confirmation before
touching anything that mutates a live order.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-mt5-history.md](010-characterize-mt5-history.md) | Characterization tests against current `engine.py` |
| [020-extract-mt5-history.md](020-extract-mt5-history.md) | Extract into standalone, tested functions |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-7's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 |
| This pack's scope | `get_total_deposits`/`compute_mt5_performance`/`import_mt5_history` only | this file |
| `update_signal` | Excluded — modifies a live MT5 order, deferred to the TP/SL-handler risk class | this file |
| Real-money surface | Read-only against the bridge for 2 of 3; `import_mt5_history` writes local DB records reconstructed from real deal history but never sends anything to MT5 | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `update_signal` (modifies live MT5 orders — see above).
- `open_trade`, `open_trade_from_signal`, `open_manual_market_order`, `close_trade`,
  `partial_close_trade`.
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing.
- Wiring the new functions back into `engine.py`.
