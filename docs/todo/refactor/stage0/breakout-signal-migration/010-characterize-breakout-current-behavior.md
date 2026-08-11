# 010 — Characterize breakout_signal's current behavior

**Status:** Done (2026-07-19) — found a real, live balance-tracking bug, see Notes
**Depends on:** none
**Real-money surface:** no
**Leverage:** same pattern as backend-foundation's 020

## Problem

`breakout_signal/database.py` (698 lines) and `engine.py` (1,686 lines) have no test coverage.
Before 020/030 touch either, current behavior needs pinning down as executable tests.

## Decision

Same approach as backend-foundation 020: characterize `database.py`'s money-path functions
exhaustively; cover `engine.py`'s pure/isolable methods and DB-backed helpers. The async
orchestration loops (`_run_cycle`, `_velocity_loop`, `_outcome_loop`, `_execute_live`,
`_run_batch_analysis`) are externally coupled the same way `gd_copy_signal`'s were (MT5 bridge,
`self._main_engine`, `core.database`, `ai_provider`/Claude) — same scope note applies, left
uncovered by design, not oversight.

## Tests first (TDD)

- `tests/breakout_signal/test_database_characterization.py` — every function in `database.py`:
  config, balance (`_update_balance`, `reconcile_balance_with_trades`, `get_max_drawdown`),
  signal CRUD, `close_signal`, `trigger_signal`, `move_sl_to_be`, `book_partial_close`,
  `expire_signal`, ML fields, `update_live_exec_result`, `update_signal_pnl_from_mt5` (this one's
  new relative to gd_copy_signal — covers the MT5-profit-overwrite path and its balance
  correction logic), stats, perf breakdowns, `get_consecutive_losses`, analysis log. Include a
  full-lifecycle killer test (create → trigger → TP1 partial → TP2 partial → close) with a
  hand-calculated expected balance.
- `tests/breakout_signal/test_engine_characterization.py` — `BreakoutEngine`'s pure/isolable
  methods: `_compute_cost_pts`, `_close_and_learn`'s P&L math (net_dol/net_pts calculation,
  ml_outcome reclassification), plus any DB-backed helpers equivalent to gd_copy_signal's
  `_level_on_cooldown`/`_already_open` if present.

## What to do

1. Write both test files against current, unmodified code; confirm they pass (characterization,
   not new-behavior TDD).
2. Prioritize `update_signal_pnl_from_mt5` and the partial-close/close_signal money math —
   highest risk, same as gd_copy_signal.

## Where

- `tests/breakout_signal/test_database_characterization.py` (new)
- `tests/breakout_signal/test_engine_characterization.py` (new)

## Acceptance

- Suite passes against current, unmodified code.
- Every money-path function in `database.py` has at least one test.
- **The killer test:** full lifecycle (create → trigger → TP1 partial → TP2 partial → close)
  matches a hand-calculated balance.

## Notes

Two raw-SQL-bypassing-the-repo spots found reading `engine.py`, beyond the close_signal/
book_partial_close atomicity gap already known from gd_copy_signal: the level-cooldown check
(`engine.py` around `_process_candidate`) and the TP2 partial's stop-loss trail update — the
latter has **no named function in `database.py` at all** (unlike gd_copy_signal, which at least
had `set_stop_loss`). 020 needs to add one.

**Real bug found (2026-07-19), reported to Simon via Telegram:** `close_signal()` applies the
*full* `net_pnl_dollars` value as the balance delta (no separate "delta still owed" parameter
like gd_copy_signal has). The real caller, `engine.py`'s `_close_and_learn`, computes
`net_dol = partial_booked + leg_net_dol` and passes that whole total into `close_signal` —
since `partial_booked` was already applied to the balance by the earlier `book_partial_close()`
calls, **every breakout trade that has at least one partial close before fully closing
double-counts that partial into the virtual balance.** Confirmed with a direct test
(`test_close_and_learn_with_prior_partial_double_counts_the_partial` in
`tests/breakout_signal/test_engine_characterization.py`) — a $15 partial + a $64.66 final leg
should total $1079.66, actually lands at $1094.66 (the $15 counted twice).

This is the app's own **virtual/simulated balance tracking** for the Breakout Engine (its
dashboard balance, drawdown, and P&L stats) — not real MT5 money; the actual account balance is
separately reconciled from real MT5 fills. `reconcile_balance_with_trades()` would self-correct
this, but it **only runs at app startup** (`database.py:125`, inside `init()`) — the live app's
process has been running continuously since 2026-07-07, so this has had no chance to
self-correct since then. Deliberately NOT fixed here — 010/020 are behavior-preserving
characterization + structural migration, not a behavior change. Characterized faithfully
(bug-preserving) in both test files; flagged as a separate, explicit fix decision for a future
task rather than silently corrected.
