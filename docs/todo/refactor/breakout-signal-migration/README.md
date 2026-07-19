# Breakout Signal Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-19

## 👋 Picking this up (agents start here)

1. Read [backend-foundation](../backend-foundation/) first if you haven't — this pack repeats
   its exact pattern (characterize → repo migration → service extraction → connectivity check)
   on the second-smallest engine, reusing the shared `DbAdapter` built in that pack's task 010.
2. Check [PROGRESS.md](PROGRESS.md) for current status.
3. Do the work from the task file (`0N0-*.md`), tests-first.
4. Update PROGRESS.md as you go.

Same ground rules as backend-foundation: TDD red/green, 800-LOC ceiling, all DB calls
transactional, never touch `/Users/simon/Documents/FOREX` or the `MooreSi/forex` remote.

## What we're building & why

Second engine in the `refactor/` migration series, after `gd_copy_signal` (done — see
backend-foundation). `breakout_signal` is next-smallest (698-line `database.py`, 1,686-line
`engine.py`, ~2,300 lines total across the module) — same shape as `gd_copy_signal`: signal
generation, TP/SL/partial-close management, live MT5 dispatch, plus two things
`gd_copy_signal` didn't have: a 3-second "velocity" loop for real-time level-cross detection,
and Claude-based batch parameter tuning (`_run_batch_analysis`) instead of VIP correlation
tracking.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-breakout-current-behavior.md](010-characterize-breakout-current-behavior.md) | Characterization tests before anything is touched |
| [020-migrate-breakout-repo-layer.md](020-migrate-breakout-repo-layer.md) | Data layer on the shared adapter, transactional |
| [030-extract-breakout-service-layer.md](030-extract-breakout-service-layer.md) | Split `engine.py` into service + focused files |
| [040-mt5-connectivity-check.md](040-mt5-connectivity-check.md) | Lighter validation, reusing the isolated MT5 terminal from backend-foundation |

## Decisions locked (2026-07-19)

| Decision | Choice | Source |
|---|---|---|
| Same pattern as gd_copy_signal | Reuse `forex_trader/src/db/` as-is, no changes | precedent |
| Scope | `breakout_signal` only. `core/engine.py`, `test_signal`, UI, MQL5 EA, sync protocol still out of scope | precedent (QUESTIONS.md #4/#7 in backend-foundation) |
| MT5 validation | Connectivity-only via the existing isolated terminal; no order round-trip (blocked by agent policy, same as before) | precedent |
| Old files | `engine.py`/`database.py` stay in place — external call sites aren't being rewired in this pack either | precedent (backend-foundation task 040 finding) |

## Building blocks we reuse

| Need | Existing code |
|---|---|
| DB adapter + transactions | `forex_trader/src/db/adapter.py`, `sqlite_adapter.py`, `connection.py` (built in backend-foundation 010) |
| Isolated MT5 terminal | `MetaTrader 5 DemoValidation` (CrossOver bottle, left in place from backend-foundation 050) |
| Decomposition pattern | `backend-conventions` §7: pure functions first, completion/tracking handlers next, transaction-wrapped writes last |

## Out of scope

- Everything backend-foundation already ruled out (UI, MQL5 EA, sync protocol, other engines).
- Wiring either this pack's or backend-foundation's new modules into the running app.
- The velocity loop's real-time behavior isn't independently load/latency-tested — only its
  logic is characterized under test, same caveat as gd_copy_signal's async loops.
