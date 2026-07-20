# 020 — Extract AI signal fallback

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` (SL
adjustment path only) -- identical call shape to the original; this pack's own tests
only ever pass a fake.

## Decision

Extract into `core_ai_signal_fallback.py` as plain functions:
`try_ai_signal_fallback(text, channel_name, tg_id, cfg, is_active_trader_node)`,
`push_ai_recovered_created(...)`, `apply_sl_adjustment(new_sl, channel_name, tg_id, via,
bridge)`, `queue_unrecognised(tg_id, channel_name, text, cfg)`,
`analyse_unrecognised_message(unrec_id, channel_name, text, cfg)` -- taking all
collaborators (`bridge`, `cfg`, `is_active_trader_node`) explicitly, no `self`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_ai_signal_fallback.py`, porting all five functions 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_ai_signal_fallback.py` (306 lines) with five
plain functions: `try_ai_signal_fallback(text, channel_name, tg_id, cfg,
is_active_trader_node, bridge)`, `push_ai_recovered_created(...)`,
`apply_sl_adjustment(new_sl, channel_name, tg_id, via, bridge)`,
`queue_unrecognised(tg_id, channel_name, text, cfg)`,
`analyse_unrecognised_message(unrec_id, channel_name, text, cfg)`. All five
live in one module so the internal calls between them
(`try_ai_signal_fallback` -> `push_ai_recovered_created`/
`apply_sl_adjustment`, `queue_unrecognised` -> `analyse_unrecognised_message`)
are direct module-level function calls, no injection needed. Imports
`_CURRENCY_RE` from `signal_parser` (already a shared module, not re-ported).
`is_active_trader_node` taken as an explicit bool parameter, not
re-extracted -- belongs to the separate startup/lifecycle cluster.

010's 17 tests ported verbatim into
`tests/core/test_ai_signal_fallback_surface.py` -- import changes only, zero
assertion changes. All 17 pass.

Full `tests/core/` suite: 727 passed. Full repo `tests/` suite: 1058 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- verified via the fake bridge's call log in both
the characterization and surface test files.
