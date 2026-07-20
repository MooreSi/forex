# Core: Trail Stop Handler Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Twentieth `core/engine.py` domain pack — sixth in the TP/SL strategy-handler cluster. Same
hard rule applies and is reconfirmed: **no real or demo MT5 order is ever placed, closed, or
modified by this pack's code, its tests, or the agent directly.**

## What we're building & why

`_handle_trail_stop` (lines 2306-2433) — `STRATEGY_TRAIL_STOP` never partial-closes; it only
moves SL. Activates when TP1 is cleared (immediately locks SL to breakeven), then every
subsequent tick trails SL behind price by a configured distance, floored (BUY) / ceilinged
(SELL) at breakeven so it never gives back the free-roll. TP2-TP5 are recorded as markers (for
the UI's TP chips) when crossed, even though nothing is actually closed at them.

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_trail_stop` | 2306-2433 | `core_handle_trail_stop.py` |

Takes `bridge` and a `TPCache` (pack 5) explicitly. Reuses
`core_tp_trigger_tracking.get_triggered_tps` (pack 5) for the TP2-5 marker scan. No partial
closes anywhere in this handler, so `partial_close_trade` (pack 9) is not needed here.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-trail-stop.md](010-characterize-handle-trail-stop.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-trail-stop.md](020-extract-handle-trail-stop.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing the TP/SL handler cluster's precedent | user, 2026-07-20 |
| This pack's scope | `_handle_trail_stop` only | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The remaining 6 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot
  commands, ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
