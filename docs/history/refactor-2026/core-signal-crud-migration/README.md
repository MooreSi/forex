# Core: Signal CRUD Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Second `core/engine.py` domain pack. Read
[core-fees-risk-governor-migration](../core-fees-risk-governor-migration/) first — same shape
applies here: `db_module.db()` is already thread-local/re-entrant, so no parallel repo module,
just plain functions.

## What we're building & why

Continuing the domain-by-domain, smallest/lowest-risk-first migration of `core/engine.py`
(10,065 lines, one `SimulationEngine` class) agreed with the user for this file. Pack 1 covered
fees/sizing/sim-account/Risk Governor. This pack covers the **signal CRUD cluster**:
`create_signal`, `get_signals`, `activate_signal`, `cancel_signal` (lines 568-633) — pure reads
and writes against the `vantage_signals` table. **No MT5 order placement anywhere in this
pack's scope** — a signal is just a proposed trade idea sitting in the database until something
else (trade-opening code, explicitly out of scope) acts on it.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `create_signal`, `get_signals`, `activate_signal`, `cancel_signal` | 568-633 | `core_signals.py` |

None of the four use `self` for anything but `db_module`, `uuid`, `time`, `json`, and
`validate_signal` (from `forex_trader.core.signal_parser`) — extract as plain functions, same
pattern as pack 1.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-signal-crud.md](010-characterize-signal-crud.md) | Characterization tests against current `engine.py` |
| [020-extract-signal-crud.md](020-extract-signal-crud.md) | Extract into standalone, tested functions |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing pack 1's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | `create_signal`/`get_signals`/`activate_signal`/`cancel_signal` only | this file |
| Real-money surface | None — no MT5 order placement, no trade-table writes, `vantage_signals` only | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in (same precedent as pack 1 and the 3 engine packs) | precedent |

## Out of scope (explicitly, for this pack)

- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- The 13 TP/SL strategy handlers, DPM, IME, the ~25 Telegram bot commands, ORB, background sync
  loops, AI fallback parsing — same deferral list as pack 1.
- Wiring the new functions back into `engine.py`.
