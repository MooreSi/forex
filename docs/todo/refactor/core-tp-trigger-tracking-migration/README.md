# Core: TP Trigger Tracking Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Fifth `core/engine.py` domain pack. Read
[core-dpm-bookkeeping-migration](../core-dpm-bookkeeping-migration/) first — same
`XCache`-container pattern applies here for the two methods that need cross-call memory.

## What we're building & why

Continuing the domain-by-domain, smallest/lowest-risk-first migration of `core/engine.py`.
Packs 1-4 covered fees/sizing/sim-account/Risk-Governor, signal CRUD, trade reporting, and DPM
bookkeeping. This pack covers **TP/SL trigger detection**: `_get_triggered_tps`,
`_last_closed_tp`, `_log_tp_wait_diagnostic`, `_check_sl`, `_check_tp_hits`,
`_get_remaining_lots` (lines 2075-2175) — every strategy handler's shared "has price hit this
level yet" logic. **Detection only — these functions never place, close, or modify a real MT5
order.** They answer "did SL/TPn get touched by this tick" and return that fact; acting on the
answer is the strategy handlers' job (explicitly out of scope, see below).

## What's different from packs 1-3 (same shape as pack 4)

Like pack 4's DPM bookkeeping, two of these six use `self` for in-memory state that isn't
derivable from the database:

- `_get_triggered_tps` — a 2.5s TTL cache (`self._tp_cache`) so every strategy handler's poll
  tick doesn't hit `vantage_partial_closes` on every call.
- `_log_tp_wait_diagnostic` — a per-trade throttle timestamp dict (`self._tp_wait_log_ts`) so
  the "still waiting for TP1" log line prints once a minute per trade instead of every poll.

Same fix as pack 4: one small `TPCache` container (`triggered: dict`, `wait_log_ts: dict`) that
callers own and pass in explicitly. `_last_closed_tp`, `_check_sl`, `_check_tp_hits` (besides
its `_get_triggered_tps` call), and `_get_remaining_lots` are plain, `self`-free.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_get_triggered_tps`, `_last_closed_tp`, `_log_tp_wait_diagnostic`, `_check_sl`, `_check_tp_hits`, `_get_remaining_lots` | 2075-2175 | `core_tp_trigger_tracking.py` |

Note: `_record_close` (out of scope — part of `close_trade`) pops a trade's entry from
`self._tp_cache` when a trade closes. That invalidation touchpoint lives outside this pack and
is untouched; the extracted `TPCache` behaves identically to `self._tp_cache` for everything
this pack's own functions do — nothing to fix or note further.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-tp-trigger-tracking.md](010-characterize-tp-trigger-tracking.md) | Characterization tests against current `engine.py` |
| [020-extract-tp-trigger-tracking.md](020-extract-tp-trigger-tracking.md) | Extract into standalone, tested functions + `TPCache` |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-4's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | The 6 trigger-detection methods only | this file |
| State-carrier shape | One small `TPCache` object, same pattern as pack 4's `DPMCache` | this file |
| Real-money surface | None — detection only, no order placement, no writes except reading `vantage_partial_closes`/`vantage_simulated_trades` | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in (same precedent as all prior packs) | precedent |

## Out of scope (explicitly, for this pack)

- The 13 TP/SL strategy handlers that consume this detection logic (`_handle_scale_out`,
  `_handle_be_runner`, etc.) — they decide what to DO with a hit, this pack only detects it.
- `_record_close`'s `self._tp_cache.pop(...)` invalidation (part of `close_trade`, deferred).
- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- DPM's own handler (`_handle_dynamic_position_management`), IME, the ~25 Telegram bot
  commands, ORB, background sync loops, AI fallback parsing — same deferral list as before.
- Wiring the new functions back into `engine.py`.
