# 020 — Migrate test_signal's data layer onto the shared adapter

**Status:** not started
**Depends on:** 010
**Real-money surface:** no

## Decision

Structural port to `test_signal_repo.py`. Key fix: consolidate `_close_signal`'s 4-way balance
update (get balance / set balance / log balance / update signal row — 4 separate connections
today) into ONE `transaction()` block via a new repo function, e.g.
`close_signal_with_balance_update(signal_id, outcome, close_price, pnl_pts, pnl_dollars,
learning_note)` that does the read-compute-write atomically. Also add named functions for the
two raw-SQL bypasses found in engine.py: the consecutive-loss check (`_run_cycle`) and the
`_reconcile_live_pnl` read of signals-with-mt5-ticket.

## Tests first (TDD)

- 010's suite, parametrized over both backends (same fixture pattern as before).
- `tests/test_signal/test_repo_transactions.py` — atomicity proof for the consolidated
  close-signal-with-balance function, plus tests for the new named functions.

## Acceptance

- 010's suite passes against both backends unmodified.
- Atomicity proven for the balance update.
- `database.py` untouched.
