# 010 — Characterize TG signals

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same DB approach as prior packs. `self._tg_reader` is replaced by a small fake test-double
exposing `get_group_name(group_id: str) -> Optional[str]`.

## Tests first (TDD)

- `tests/core/test_tg_signals_characterization.py`:
  - Excludes `status='instant_historical'` rows.
  - Orders by `parsed_at` descending; respects `limit`.
  - Backfills `group_name` from `tg_reader.get_group_name(...)` only when the row's own
    `group_name` is falsy.
  - Leaves `group_name` alone when already set (never overwrites).
  - Works with `tg_reader=None` (no enrichment attempted, no crash) -- matches
    `self._tg_reader` being falsy/unset in the original.

## What to do

1. Write the test file against `SimulationEngine.get_tg_signals`, using
   `SimulationEngine.__new__(SimulationEngine)` with `_tg_reader` set manually to a fake
   test-double (or `None`).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from prior packs.

## Notes

6 tests written in `tests/core/test_tg_signals_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. Confirmed `group_name` backfill only fires
when the row's own value is falsy AND a `tg_reader` is present; `tg_reader=None` (matching an
unset `self._tg_reader`) is handled without any special-casing needed in the test.
