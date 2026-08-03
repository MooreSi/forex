# Core: ORB Fixed Handler Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Sixteenth `core/engine.py` domain pack — first pack in a new cluster: the 13 TP/SL strategy
handlers that run in the tick loop and act on pack 5's TP/SL detection logic. Same hard rule
applies and is reconfirmed: **no real or demo MT5 order is ever placed, closed, or modified by
this pack's code, its tests, or the agent directly.**

## What we're building & why

`_handle_orb_fixed` (lines 2662-2700) — the ORB/IVB Report strategy's TP/SL handler. By far
the simplest of the 13: "exactly the setup the report computed, nothing recalculated." SL is
already handled generically elsewhere (`_check_sl`, out of scope); this handler's only job is
a full close (no partials, no BE-move, no trailing) the instant `tp1` (the report's own target)
is hit.

## Why this one first

Surveyed all 13 handlers before picking: most (`_handle_scale_out`, `_handle_scalp_runner`,
`_handle_conservative_trial`, `_handle_no_sl_scale`, etc.) are 100-200+ lines with retry-cooldown
instance-state dicts, breakeven-SL-move logic, and multiple `bridge.modify_order`/
`bridge.partial_close` call sites. `_handle_orb_fixed` has none of that — a single
`bridge.partial_close` call, no instance state, no SL modification — the cleanest possible
entry point into this cluster, same reasoning as choosing `partial_close_trade` first in the
trade-management cluster (pack 9).

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_orb_fixed` | 2662-2700 | `core_handle_orb_fixed.py` |

Takes `bridge` and a `TPCache` (pack 5) explicitly instead of `self._bridge`/`self._tp_cache`.
Reuses `core_tp_trigger_tracking.check_tp_hits`/`get_remaining_lots` (pack 5),
`core_partial_close.partial_close_trade` (pack 9). Calls `telegram_alerts.fmt_tp_hit`/
`send_message` directly (both already confirmed safe to call for real against a test DB, per
pack 10's characterization).

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-orb-fixed.md](010-characterize-handle-orb-fixed.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-orb-fixed.md](020-extract-handle-orb-fixed.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | New cluster (TP/SL strategy handlers), smallest/lowest-risk first, same as every prior cluster | user, 2026-07-20 |
| This pack's scope | `_handle_orb_fixed` only | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The other 12 TP/SL strategy handlers — each gets its own scoping pass given the size/state
  variance surveyed above.
- DPM's own handler, IME, the ~25 Telegram bot commands, ORB report generation itself
  (`build_orb_report`), background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
