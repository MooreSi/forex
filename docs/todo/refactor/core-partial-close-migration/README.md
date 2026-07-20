# Core: Partial Close Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Ninth `core/engine.py` domain pack — first pack in the real-money-adjacent trade-management
cluster (`open_trade`/`open_trade_from_signal`/`open_manual_market_order`/`close_trade`/
`partial_close_trade`), entered only after explicit user authorization to characterize/extract
this code using mock bridges, with a hard rule that **no order is ever placed or modified for
real** — not by this pack's code, not by its tests, not by the agent directly. See
[core-mt5-history-migration](../core-mt5-history-migration/) for the immediately-preceding
pack and the same "take collaborators as explicit parameters" pattern.

## What we're building & why

`partial_close_trade` (line 1833) — records a partial close (a TP level banking some lots)
against an already-open trade: writes a `vantage_partial_closes` row, updates
`remaining_lots`/`realised_pnl`/`net_pnl` on the trade, updates the sim balance, optionally
moves SL to breakeven after TP1, and closes the trade out entirely if `remaining_lots` hits
zero. **It never calls the MT5 bridge** — the actual broker-side partial close (an MT5
`close_position` call for the closed lots) happens in the strategy-handler call site before
this method runs; `partial_close_trade` only does the DB-side bookkeeping afterward. That
makes it meaningfully lower-risk than `close_trade` (which calls `bridge.close_position`
directly) or the `open_*` methods — the natural next-smallest step into this cluster.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `partial_close_trade` | 1833-1892 | `core_partial_close.py` |

Calls `self.pnl(...)` — replaced with pack 1's `core_fees_sizing.pnl()`, same as pack 8's
`import_mt5_history`.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-partial-close.md](010-characterize-partial-close.md) | Characterization tests against current `engine.py` |
| [020-extract-partial-close.md](020-extract-partial-close.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-8's precedent, now inside the trade-management cluster: smallest/lowest-risk sub-piece first | user, 2026-07-20 |
| This pack's scope | `partial_close_trade` only — the one trade-management method with no direct bridge call | this file |
| Order-placement boundary | Hard rule, reconfirmed: no real or demo MT5 order is ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- `close_trade`/`_record_close` — calls `bridge.close_position` directly, plus is deeply
  coupled to telegram alerts, `sync.ledger`, DPM finalization, Risk Governor halt checks, and
  the circuit breaker. Meaningfully bigger/riskier than this pack; will get its own dedicated
  scoping pass.
- `open_trade`, `open_trade_from_signal`, `open_manual_market_order` — real order placement,
  the largest and most complex methods in `core/engine.py` (`open_trade_from_signal` alone is
  ~500 lines). Not started.
- `update_signal` (modifies a live MT5 order — see pack 8's README).
- The 13 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot commands, ORB,
  background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
