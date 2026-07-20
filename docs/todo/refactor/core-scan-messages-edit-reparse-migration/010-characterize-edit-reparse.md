# 010 — Characterize edit/re-parse state machine

**Status:** Done (2026-07-20)
**Depends on:** none (reuses `core_ai_signal_fallback`, `core_instant_followup`,
`core_close_trade`, all already extracted and independently characterized)
**Real-money surface:** the instant-entry-flip-flatten branch calls
`close_trade` on a real open position -- faked in every test here.

## Decision

No separate original method exists for this block (it's inline in
`_scan_messages`), so characterization drives the whole method for one
scan cycle via a fake `_tg_reader` (`get_buffer_messages`/
`get_active_group_slots`/`get_group_name`) and a pre-seeded
`vantage_tg_signals` row matching each scenario, with
`_try_ai_signal_fallback`/`_find_and_apply_instant_followup`/`close_trade`
faked on the class so each test isolates this block's own control flow.
Real GD2-format signal text (reused from `tests/test_signal_parser.py`'s
own fixtures) drives the deterministic-parse paths; bare "XAU USD SELL NOW"
triggers the instant-entry-fix path.

Every branch pre-traced via throwaway scripts first, given the depth of
nesting (dedup -> re-parse success/failure -> same-direction/flipped ->
instant-fix -> AI-fallback, five layers deep in the worst case).

## Tests first (TDD)

- `tests/core/test_scan_messages_edit_reparse_characterization.py`:
  - Text unchanged since last seen -> dedup skip, no DB write.
  - Text changed, full re-parse, same direction, status `"new"` -> all
    fields updated, `_find_and_apply_instant_followup` called with the new
    parsed signal.
  - Full re-parse, same direction, status `"pending_followup"` -> status
    flips to `"new"` and the message promotes to the execution flow
    (verified at the DB-row level, not by driving the downstream execution
    logic itself -- that's sub-packs B/C/D's own scope).
  - Re-parse returns no entry data (non-signal text edit), no matching
    instant status -> `raw_text` updated only, AI fallback attempted and
    failing -> dropped (message ID converges on next scan).
  - Full re-parse, direction flipped, status `"new"` -> signal corrected
    in place, a "SIGNAL CORRECTED via edit" alert sent.
  - Full re-parse, direction flipped, status `"activated"` (already
    executed) -> `raw_text` updated only (so future scans converge), a
    "SIGNAL EDIT WARNING" alert sent, no auto-correction.
  - Re-parse fails, status `"instant_activated"`, instant-trigger parse
    finds a direction flip, a matching open trade exists (same
    `tg_source`, same prior direction) -> `close_trade` called with
    `reason="instant_edit_flip:<old>-><new>"`, an "INSTANT SIGNAL
    CORRECTED via edit" alert reporting the closed trade ID.
  - Same, but no matching open trade -> alert reports "no matching open
    trade found — nothing to close", no `close_trade` call.
  - Same, but `close_trade` raises -> alert reports the failure text, no
    crash.
  - Re-parse fails, instant-trigger parse finds the SAME direction (still
    bare) -> `raw_text` re-synced only, no alert, no close.
  - Re-parse fails, status not an instant one (or instant-trigger parse
    also fails) -> AI fallback attempted; fails -> dropped.
  - AI fallback succeeds, same direction -> re-enters the same
    full-update path as the deterministic-success case.
  - AI fallback succeeds, direction flipped, status `"new"` -> re-enters
    the same in-place-correction-and-alert path.

## What to do

1. Write the test file using a fake `_tg_reader` and faked collaborators,
   calling `_scan_messages` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- `close_trade`
  is always faked.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

13 tests written in `tests/core/test_scan_messages_edit_reparse_characterization.py`,
all green on the first run against unmodified `engine.py` after fixing the
same missing-`self`-parameter mock issue seen in several prior packs when
faking `close_trade`/`_try_ai_signal_fallback` directly on the class. No
`engine.py` bugs found across any of the branches.
