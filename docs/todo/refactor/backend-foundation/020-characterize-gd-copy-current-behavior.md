# 020 — Characterize gd_copy_signal's current behavior

**Status:** not started
**Depends on:** none (can run in parallel with 010)
**Real-money surface:** no
**Leverage:** none — new ground (only 2 real test files exist in the whole live app today,
covering `core/engine.py` and the signal parser — neither touches `gd_copy_signal`)

## Problem

`gd_copy_signal/database.py` (752 lines) and `engine.py` (1,295 lines) have zero test coverage
today. Before either is touched in 030/040, their current behavior needs to be pinned down as
executable tests, so a refactor that silently changes behavior gets caught immediately instead
of discovered live.

## Decision

Write characterization tests against the CURRENT, unmodified `gd_copy_signal/database.py` and
`engine.py` (as forked into `forex-refactor2` — no changes yet). Prioritize the money-path
functions first (signal CRUD, balance updates, partial closes, stats), since those are
highest-risk; lighter coverage for config/level-tracking/research helpers.

## Tests first (TDD)

- `tests/gd_copy_signal/test_database_characterization.py` — covers `init`/schema creation,
  `create_signal`, `get_open_signals`/`get_all_signals`/`get_signal_by_id`, `trigger_signal`,
  `close_signal` (incl. balance update), `move_sl_to_be`, `set_stop_loss`, `book_partial_close`
  (remaining-fraction math, balance delta), `expire_signal`, the ML fields, correlation
  update + `log_near_miss` idempotency, `update_live_exec`, `get_stats`, the perf-breakdown
  functions, `upsert_level` (strength increment within the price-tolerance window), config
  get/set, balance reconcile/drawdown.
- `tests/gd_copy_signal/test_engine_characterization.py` — covers `engine.py`'s public entry
  points (signal generation trigger conditions, TP/SL/partial-close orchestration,
  correlation-tracking call-through into `database.py`), mocking only true externals (MT5
  bridge, Telegram) — the database layer runs for real against a temp file, not mocked.

## What to do

1. Read `gd_copy_signal/engine.py` in full to map its public surface and side effects.
2. Write `test_database_characterization.py` against the real module, using a fresh temp-file
   SQLite DB per test.
3. Write `test_engine_characterization.py`.
4. Run the full suite, confirm everything passes against current, unmodified code — this is a
   characterization suite describing what already exists, not red/green TDD for new behavior,
   so it should go green immediately.

## Where

- `tests/gd_copy_signal/test_database_characterization.py` (new — a partial draft exists from
  the abandoned `forex-refactor` attempt and can be ported over as a starting point)
- `tests/gd_copy_signal/test_engine_characterization.py` (new)

## Acceptance

- Suite passes against current, unmodified `gd_copy_signal` code.
- Every money-path function in `database.py` (create/trigger/close/partial-close/balance) has
  at least one test.
- **The killer test:** a full lifecycle test — create a signal, trigger it, book a TP1 partial,
  close the remainder — asserting the final balance matches a hand-calculated expected value.
  This is the test 030 and 040 must keep passing unmodified.

## Notes

This suite is the safety net for 030 and 040. Don't thin it out to save time — it's the entire
point of doing this before restructuring anything.
