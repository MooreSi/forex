# Core: DPM Bookkeeping Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Fourth `core/engine.py` domain pack. Read
[core-fees-risk-governor-migration](../core-fees-risk-governor-migration/) first for the base
pattern. **This pack is a partial exception to "plain functions, no state carrier"** — see
"What's different" below before assuming pack 1-3's shape applies unchanged.

## What we're building & why

Continuing the domain-by-domain, smallest/lowest-risk-first migration of `core/engine.py`.
Packs 1-3 covered fees/sizing/sim-account/Risk-Governor, signal CRUD, and trade reporting. This
pack covers **DPM (Dynamic Position Management) bookkeeping**: `_load_dpm_calibrated`,
`_record_dpm_entry`, `_update_dpm_peak`, `_set_dpm_milestone`, `_finalize_dpm_record`
(lines 3426-3545) — reads/writes against `dpm_trade_performance` and `dpm_calibration`, plus an
in-process TTL cache for calibrated multipliers. **No MT5 order placement, no trade-table
writes — this only tracks DPM's own analytics/calibration side tables.**

## What's different from packs 1-3

Unlike every method in packs 1-3, three of these five genuinely use `self` for **in-memory
state that isn't derivable from the database**:

- `_load_dpm_calibrated` — TTL-cached (`self._dpm_cal_loaded_at`, refreshed at most once per
  10 minutes) copy of the calibrated multiplier table (`self._dpm_calibrated`).
- `_record_dpm_entry` — dedup guard (`self._dpm_recorded: set[str]`) so a trade's entry
  snapshot is only ever inserted once, even though the method is called every monitor-loop
  tick for every open trade.

`_update_dpm_peak`, `_set_dpm_milestone`, `_finalize_dpm_record` are plain `self`-free reads/
writes, same shape as packs 1-3.

**Consequence:** rather than force these into stateless functions (which would just move the
cache into some other global, no real improvement) or build a full mixin class (overkill for
5 methods), this pack introduces one small `DPMCache` container — a plain object holding
`calibrated: dict`, `loaded_at: float`, `recorded: set[str]` — that callers own and pass in
explicitly. This is the smallest change that keeps the caching honest and testable without
reintroducing hidden global/instance state.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `_load_dpm_calibrated`, `_record_dpm_entry` (need `DPMCache`), `_update_dpm_peak`, `_set_dpm_milestone`, `_finalize_dpm_record` (stateless) | 3426-3545 | `core_dpm_bookkeeping.py` |

`_run_dpm_calibration` (line 3547, the background calibration loop that writes
`dpm_calibration` and resets the TTL cache) is **out of scope** — it's a much larger, `asyncio`-
driven background job, a different risk/size class from this pack's simple bookkeeping calls.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-dpm-bookkeeping.md](010-characterize-dpm-bookkeeping.md) | Characterization tests against current `engine.py` |
| [020-extract-dpm-bookkeeping.md](020-extract-dpm-bookkeeping.md) | Extract into standalone, tested functions + `DPMCache` |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-3's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | The 5 bookkeeping methods only; `_run_dpm_calibration` deferred | this file |
| State-carrier shape | One small `DPMCache` object (not a mixin, not hidden globals) for the 2 methods that need cross-call memory | this file, given the constraint of "no logic changes" |
| Real-money surface | None — no MT5 order placement, no trade-table writes, DPM analytics tables only | verified by reading the code |
| `engine.py` itself | Left untouched — new functions exist standalone/tested, not wired in (same precedent as packs 1-3 and the 3 engine packs) | precedent |

## Out of scope (explicitly, for this pack)

- `_run_dpm_calibration` (background calibration loop).
- `_handle_dynamic_position_management` (the TP/SL strategy handler that calls these
  bookkeeping methods) — part of the 13 TP/SL strategy handlers, deferred like the rest.
- `open_trade`, `open_trade_from_signal`, `close_trade`, `partial_close_trade` and everything
  else that places or closes a real MT5 order.
- The other 12 TP/SL strategy handlers, IME, the ~25 Telegram bot commands, ORB, background
  sync loops, AI fallback parsing — same deferral list as packs 1-3.
- Wiring the new functions back into `engine.py`.
