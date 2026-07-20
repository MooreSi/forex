# 010 — Characterize signal CRUD

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same approach as pack 1's 010: characterize against the real `forex_trader.core.database`
module (`db_module`), using a temp file passed to `db_module.init()` so nothing touches real
app data, but the real shared schema (`vantage_signals`).

## Tests first (TDD)

- `tests/core/test_signal_crud_characterization.py`:
  - `create_signal` — happy path (returns `{signal_id, status: "pending"}`, row inserted with
    correct fields); validation errors from `validate_signal` propagate as `ValueError`;
    `require_at_least_tp1` risk-setting gate raises when `tp1` is `None` and the setting is on.
  - `get_signals` — no filter returns all, newest first; `status` filter narrows correctly;
    `claude_commentary` JSON column is parsed into a dict when present, left alone/ignored on
    bad JSON.
  - `activate_signal` — pending → active transition sets `activated_at`; raises on unknown
    signal_id; raises when status isn't `pending` (e.g. already active or cancelled).
  - `cancel_signal` — sets status to `cancelled` and `cancelled_at`.

## What to do

1. Write the test file against `SimulationEngine`'s real methods (called via
   `SimulationEngine.method(None, ...)` — none of the four need `self`).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from pack 1 (same
  `db_module.db()` thread-local caching gotcha applies here too).

## Notes

12 tests written in `tests/core/test_signal_crud_characterization.py`, all green against
unmodified `engine.py` on first run -- no bugs found in this cluster (unlike pack 1's
`_rg_apply_halts_on_close` gap, there's no multi-statement sequence here that isn't already a
single `db_module.db()` block per method). `require_at_least_tp1` confirmed to default to `1`
(enabled) in the `vantage_risk_settings` schema. `claude_commentary` is a raw TEXT column on
`vantage_signals`; `get_signals` best-effort `json.loads`s it and leaves the raw string in place
on a parse failure -- both paths characterized.
