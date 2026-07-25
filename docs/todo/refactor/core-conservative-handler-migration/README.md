# Core: Conservative Handler Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Twenty-second `core/engine.py` domain pack — eighth in the TP/SL strategy-handler cluster.
Same hard rule applies and is reconfirmed: **no real or demo MT5 order is ever placed, closed,
or modified by this pack's code, its tests, or the agent directly.**

## What we're building & why

`_handle_conservative` (lines 2541-2660) — `STRATEGY_CONSERVATIVE`'s tick-loop management
(distinct from the fixed-point SL/TP1 the signal opens with, already covered by pack 13's
post-fill override). Two mutually-exclusive phases within a single call:

1. **Before TP1**: waits for TP1, then closes 80% of the position and moves SL to breakeven —
   returns immediately afterward (never falls through to phase 2 in the same call).
2. **After TP1** (on a later call): trails the remaining 20% with a fixed 3pt stop, floored at
   breakeven.

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_conservative` | 2541-2660 | `core_handle_conservative.py` |

Takes `bridge`, a `TPCache` (pack 5), and `close_full_after_tps` (optional injected callable)
explicitly. Reuses `core_tp_trigger_tracking.get_triggered_tps`/`log_tp_wait_diagnostic`/
`get_remaining_lots` (pack 5), `core_partial_close.partial_close_trade` (pack 9).

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-conservative.md](010-characterize-handle-conservative.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-conservative.md](020-extract-handle-conservative.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing the TP/SL handler cluster's precedent | user, 2026-07-20 |
| This pack's scope | `_handle_conservative` only | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The remaining 3 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot
  commands, ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
