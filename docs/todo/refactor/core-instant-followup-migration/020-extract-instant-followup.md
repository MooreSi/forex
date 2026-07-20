# 020 — Extract IME follow-up flow

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order's SL/TP via `bridge.modify_order`
-- identical call shape to the original; this pack's own tests only ever pass
a fake.

## Decision

Extract into `core_instant_followup.py` as three plain functions:
`apply_followup_to_instant_trade(instant_trade, parsed, tg_id, channel_name,
source_label, bridge)`, `find_and_apply_instant_followup(channel_name,
direction, parsed, tg_id, bridge)`, `ime_timeout_watchdog(tick, bridge)` --
taking `bridge` explicitly, no `self`. Calls `core_update_signal.update_signal`
directly (already extracted).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_instant_followup.py`, porting all three functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_instant_followup.py` (388 lines) with three
plain functions: `apply_followup_to_instant_trade(instant_trade, parsed,
tg_id, channel_name, source_label, bridge)`,
`find_and_apply_instant_followup(channel_name, direction, parsed, tg_id,
bridge)`, `ime_timeout_watchdog(tick, bridge)`, porting all three 1:1.
`find_and_apply_instant_followup` calls `apply_followup_to_instant_trade` as
a direct module-level sibling call. Reuses `core_update_signal.update_signal`
(already extracted) for the signal-linked apply path.

010's 13 tests ported verbatim into
`tests/core/test_instant_followup_surface.py` -- import changes only, zero
assertion changes. All 13 pass, including the unconditional-`modify_order`
finding from 010.

Full `tests/core/` suite: 823 passed. Full repo `tests/` suite: 1154 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- verified via the fake bridge's call log in both
the characterization and surface test files.

This closes out the IME (Instant Market Entry) cluster
(core-instant-entry-migration + core-instant-followup-migration).
