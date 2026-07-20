# 010 — Characterize untracked MT5 positions

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** no

## Decision

Same DB approach as prior packs. `self._bridge` is replaced by a small fake test-double
(`_FakeBridge`) exposing sync `is_configured()` and async `get_positions()`, since constructing
a real `MT5BridgeClient` would need an actual HTTP endpoint.

## Tests first (TDD)

- `tests/core/test_untracked_positions_characterization.py`:
  - Returns `[]` when the bridge isn't configured (never calls `get_positions()`).
  - Returns `[]` when `get_positions()` raises (caught, not propagated).
  - Returns `[]` when the bridge returns no live positions.
  - Returns positions whose ticket has no matching `mt5_ticket` in `get_open_trades()`, each
    tagged `_untracked=True`.
  - Excludes positions whose ticket DOES match an open trade's `mt5_ticket`.

## What to do

1. Write the test file against `SimulationEngine.get_untracked_mt5_positions`, with a
   `_FakeEngine` exposing `_bridge` (the fake bridge) so `self.get_open_trades()` inside it
   still needs a real bound method -- use `SimulationEngine.__new__(SimulationEngine)` with
   `_bridge` set manually (same instance-construction pattern as pack 5).
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- Reuses the `_reset_thread_local_connection()` fixture pattern from prior packs.

## Notes

5 tests written in `tests/core/test_untracked_positions_characterization.py`, all green against
unmodified `engine.py` on first run. No bugs found. `_FakeBridge` is a plain object (sync
`is_configured`, async `get_positions`) -- no HTTP client, no live MT5 connection ever
constructed. Confirmed the exception-swallowing (`get_positions()` raising returns `[]`, not
propagated) and the not-configured short-circuit (never calls `get_positions()` at all).
