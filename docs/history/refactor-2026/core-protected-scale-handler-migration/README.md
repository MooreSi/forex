# Core: Protected Scale Handler Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Twenty-first `core/engine.py` domain pack — seventh in the TP/SL strategy-handler cluster.
Same hard rule applies and is reconfirmed: **no real or demo MT5 order is ever placed, closed,
or modified by this pack's code, its tests, or the agent directly.**

## What we're building & why

`_handle_protected_scale` (lines 2435-2540) — a three-phase strategy:

1. **TP1**: deliberately skipped — marked `TP1_SKIPPED` so it's never re-processed, but no
   close and no SL move happen.
2. **TP2**: moves SL to breakeven (marked `TP2_BE_LOCKED`) — pure protection, still no partial
   close.
3. **TP3-5**: each closes a flat 20% of the original lot size.

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_protected_scale` | 2435-2540 | `core_handle_protected_scale.py` |

Takes `bridge`, a `TPCache` (pack 5), and `close_full_after_tps` (optional injected callable,
same as packs 17/19) explicitly. Reuses `core_tp_trigger_tracking.get_triggered_tps`/
`get_remaining_lots` (pack 5), `core_partial_close.partial_close_trade` (pack 9).

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-protected-scale.md](010-characterize-handle-protected-scale.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-protected-scale.md](020-extract-handle-protected-scale.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing the TP/SL handler cluster's precedent | user, 2026-07-20 |
| This pack's scope | `_handle_protected_scale` only | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The remaining 5 TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot
  commands, ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
