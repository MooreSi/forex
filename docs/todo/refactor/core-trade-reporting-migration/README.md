# Core: Trade Reporting Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Third `core/engine.py` domain pack. Read
[core-fees-risk-governor-migration](../core-fees-risk-governor-migration/) first for the base
pattern — same shape applies: `db_module.db()` is already thread-local/re-entrant, so no
parallel repo module, just plain functions.

## What we're building & why

Continuing the domain-by-domain, smallest/lowest-risk-first migration of `core/engine.py`.
Packs 1-2 covered fees/sizing/sim-account/Risk-Governor and signal CRUD. This pack covers
**read-only trade reporting**: `get_open_trades`, `get_all_trades`, `compute_performance`
(lines 1894-2071) — pure `SELECT`s against `vantage_simulated_trades`/`vantage_simulation_account`
plus in-Python aggregation (win rate, Sharpe/Sortino, drawdown, daily stats). **No writes, no
MT5 order placement anywhere in this pack's scope.**

`get_untracked_mt5_positions` (line 1916, sits between `get_open_trades` and `get_all_trades`
in the file) is explicitly **deferred**, not included here: it's `async`, calls the live MT5
bridge (`self._bridge.get_positions()`), and depends on `get_open_trades`. It's a read, not an
order placement, but the bridge dependency makes it a meaningfully different (and slightly
higher-risk / harder to test in isolation) shape than the three pure-DB functions in this pack —
better as its own small future pack alongside other bridge-dependent reads.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `get_open_trades`, `get_all_trades`, `compute_performance` | 1894-2071 | `core_trade_reporting.py` |

`compute_performance` reads `self._cfg.get("starting_balance", 1000.0)` — the only
not-quite-`self`-free method in this pack. Same pattern as pack 1's `reset_simulation`: extract
as a function taking `starting_balance: float` as an explicit parameter instead of reading
instance config.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-trade-reporting.md](010-characterize-trade-reporting.md) | Characterization tests against current `engine.py` |
| [020-extract-trade-reporting.md](020-extract-trade-reporting.md) | Extract into standalone, tested functions |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-2's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | `get_open_trades`/`get_all_trades`/`compute_performance` only | this file |
| `get_untracked_mt5_positions` | Deferred — bridge-dependent, different shape, own future pack | this file |
| Real-money surface | None — read-only, no MT5 order placement, no writes | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in (same precedent as packs 1-2 and the 3 engine packs) | precedent |

## Out of scope (explicitly, for this pack)

- `get_untracked_mt5_positions` (bridge-dependent).
- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- The 13 TP/SL strategy handlers, DPM, IME, the ~25 Telegram bot commands, ORB, background sync
  loops, AI fallback parsing — same deferral list as packs 1-2.
- Wiring the new functions back into `engine.py`.
