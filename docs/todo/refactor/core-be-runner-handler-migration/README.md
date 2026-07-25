# Core: BE Runner Handler Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Eighteenth `core/engine.py` domain pack — third in the TP/SL strategy-handler cluster, after
packs 16 (`_handle_orb_fixed`) and 17 (`_handle_scale_out`). Same hard rule applies and is
reconfirmed: **no real or demo MT5 order is ever placed, closed, or modified by this pack's
code, its tests, or the agent directly.**

## What we're building & why

`_handle_be_runner` (lines 2249-2304) — `STRATEGY_BE_RUNNER` holds the full position (no
partial closes) and ratchets SL up through the signal's own TP ladder as each level is crossed,
letting MT5 close the whole thing at the final TP. ADX-gated: falls back entirely to Scale Out
(pack 17) when the market isn't trending (`ADX < 25`).

## Target method (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_handle_be_runner` | 2249-2304 | `core_handle_be_runner.py` |

Takes `bridge`, `dpm_candles`, and pack 17's `handle_scale_out` collaborator set
(`tp_cache`/`scale_out_last_fail`/`close_full_after_tps`) explicitly, since the ADX-ranging
fallback needs all of them to call `core_handle_scale_out.handle_scale_out` directly.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-handle-be-runner.md](010-characterize-handle-be-runner.md) | Characterization tests against current `engine.py` |
| [020-extract-handle-be-runner.md](020-extract-handle-be-runner.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 16-17's precedent in the TP/SL handler cluster | user, 2026-07-20 |
| This pack's scope | `_handle_be_runner` only | this file |
| Order-placement/modification boundary | Hard rule, reconfirmed: no real/demo MT5 order ever placed/closed/modified by this work. Tests use fakes only. | user, 2026-07-20 (standing) |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

- The other 10 remaining TP/SL strategy handlers, DPM's own handler, IME, the ~25 Telegram bot
  commands, ORB report generation, background sync loops, AI fallback parsing.
- Wiring the new function back into `engine.py`.
