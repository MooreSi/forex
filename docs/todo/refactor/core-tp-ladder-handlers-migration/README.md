# Core: TP Ladder Handlers Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Nineteenth `core/engine.py` domain pack — fourth in the TP/SL strategy-handler cluster. Bundles
`_run_tp_ladder` (the shared TP-ladder walk engine) with its three thin wrapper handlers
(`_handle_signal_climber`, `_handle_gd_vip_runner`, `_handle_adaptive_runner`) into one pack,
since the wrappers are each a single-line call into the shared engine with different
parameters — extracting them separately would be pure busywork. Same hard rule applies and is
reconfirmed: **no real or demo MT5 order is ever placed, closed, or modified by this pack's
code, its tests, or the agent directly.**

## What we're building & why

`_run_tp_ladder` (lines 2895-3015) walks a signal's TP ladder in order: closes a percentage of
the lot at each TP (per a strategy-specific close-schedule table keyed by TP count), moves SL
to breakeven at a configurable rung (`be_at_pos`), then trails SL to the previous TP's price on
every subsequent TP. The three strategies that use it differ only in which close-schedule table
and `be_at_pos` they pass:

| Strategy | Table | `be_at_pos` | Why |
|---|---|---|---|
| Signal Climber | `_CLIMBER_PCTS` | 0 (TP1) | Front-loaded exits, uses the signal's SL/TPs exactly |
| GD VIP Runner | `_GDVR_PCTS` | 1 (TP2) | Back-loaded exits; SL already widened at open, BE delayed to TP2 so the wider stop isn't given up early |
| Adaptive Runner | `_GDVR_PCTS` | 0 (TP1) | Same back-loaded table as GD VIP Runner, but the widened SL is capped relative to the final TP, so BE can happen at TP1 without giving up the point of the cap |

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_run_tp_ladder`, `_handle_signal_climber`, `_handle_gd_vip_runner`, `_handle_adaptive_runner` | 2841-3015 | `core_run_tp_ladder.py` |

Takes `bridge`, a `TPCache` (pack 5), and `close_full_after_tps` (optional injected callable,
same as pack 17) explicitly. Reuses `core_tp_trigger_tracking.get_triggered_tps`/
`log_tp_wait_diagnostic`/`get_remaining_lots` (pack 5), `core_partial_close.partial_close_trade`
(pack 9), and pack 11's already-ported `_CLIMBER_PCTS`/`_GDVR_PCTS` tables (`core_open_trade.py`,
ported there for the EA-ladder lookup) instead of duplicating them a third time.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-run-tp-ladder.md](010-characterize-run-tp-ladder.md) | Characterization tests against current `engine.py` |
| [020-extract-run-tp-ladder.md](020-extract-run-tp-ladder.md) | Extract into standalone, tested functions |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Bundle the shared engine with its 3 thin wrappers, same reasoning as pack 1's 3-in-1 structure | this file, given the wrappers have no logic of their own |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The remaining 7 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot
  commands, ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new functions back into `engine.py`.
