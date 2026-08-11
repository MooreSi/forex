# Core: Fees, Sizing, Sim Account, Risk Governor Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Read [backend-foundation](../backend-foundation/) first for the base pattern. This pack is
**architecturally different** from the three engine packs (gd_copy_signal, breakout_signal,
test_signal) — read "What's different" below before assuming the same shape applies.

## What we're building & why

First slice of `core/engine.py` (10,065 lines, one `SimulationEngine` class, 140 methods) — by
far the largest remaining piece of the `refactor/` series, and qualitatively different from the
three engines already done: it's the shared kernel that actually places real MT5 orders for
every other engine, not just its own virtual tracking. Given the scale (~20 distinct domains:
trade opening/closing, 13 TP/SL strategy handlers, DPM, Risk Governor, IME instant-entry
parsing, ~25 Telegram bot commands, background sync loops, ORB, AI fallback parsing), this is
being broken into one domain-scoped pack at a time, smallest/lowest-risk first — not one giant
pack like the engines got.

This first pack covers the **lowest-risk cluster**: fee calculation, lot sizing, the sim
account ledger, and the Risk Governor's sizing/halt logic. All pure computation or simple
reads/writes — **no MT5 order placement anywhere in this pack's scope.**

## What's different from the engine packs

`gd_copy_signal`, `breakout_signal`, and `test_signal` each had their own **isolated** SQLite
database (`gd_copy_signal.db` etc.) with a naive raw-`sqlite3`-per-call pattern and no
atomicity — that's why each got a parallel `_repo.py` built on a new `DbAdapter`.

`core/engine.py` instead reads/writes through `forex_trader/core/database.py` (`db_module`) —
**the single shared database every engine and the UI use.** Critically, `db_module.db()` is
**already thread-local and re-entrant**: nested `with db_module.db():` calls on the same thread
share one connection and only the outermost commits. This is functionally the same guarantee
the other three packs' `transaction()` had to be built from scratch to get — `core/database.py`
already has it.

**Consequence: no parallel repo module for this pack.** Where a real atomicity gap exists (two
sequential top-level `db_module.db()` calls that should be one unit), the fix is just wrapping
the call site in an outer `with db_module.db():` block — the existing re-entrancy makes the
inner calls participate automatically. Much smaller surface than rebuilding a database layer.

**Also: none of this pack's target methods need `self`.** `calculate_fees`, `pnl`,
`suggest_lot_size`, the sim-account functions, and the Risk Governor functions only touch
`db_module` and their own parameters — no `SimulationEngine` instance state. They extract
cleanly as plain functions, not mixins.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `calculate_fees`, `pnl`, `suggest_lot_size` | 492-536 | `core_fees_sizing.py` |
| `get_sim_account`, `update_sim_balance`, `reset_simulation` | 540-564 | `core_sim_account.py` |
| `is_trading_paused`, `_price_in_entry_range`, `_check_pre_trade_filters`, `_rg_day_start_ts`, `_rg_size_and_check`, `_rg_check_halt`, `_rg_apply_halts_on_close` | 3831-4068 | `core_risk_governor.py` |

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-fees-sizing-risk-governor.md](010-characterize-fees-sizing-risk-governor.md) | Characterization tests against current `engine.py` |
| [020-extract-fees-sizing-risk-governor.md](020-extract-fees-sizing-risk-governor.md) | Extract into standalone, tested functions; fix the one real atomicity gap found |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | One `core/engine.py` domain per pack, smallest/lowest-risk first, NOT one giant pack | user, 2026-07-20 |
| This pack's scope | Fees/sizing/sim-account/Risk-Governor only. Trade opening/closing, TP/SL handlers, DPM, bot commands, IME all explicitly deferred to later packs | user, 2026-07-20 |
| Real-money surface | None in this pack — no MT5 order placement anywhere in the target methods | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in (matches the 3 engine packs' precedent) | precedent |

## Out of scope (explicitly, for this pack)

- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- The 13 TP/SL strategy handlers (`_handle_scale_out`, `_handle_be_runner`, etc.).
- DPM, IME, the ~25 Telegram bot commands, ORB, background sync loops, AI fallback parsing.
- Wiring the new functions back into `engine.py` — a later, separate decision (same as the
  engine packs).
