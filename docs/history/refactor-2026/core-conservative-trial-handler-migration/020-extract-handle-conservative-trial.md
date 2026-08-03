# 020 — Extract _handle_conservative_trial

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- identical call shape to the original; this
pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_conservative_trial.py` as a single plain async function taking
`bridge`, a `TPCache` (pack 5), and `close_full_after_tps` (optional injected callable, same
pattern as packs 17/19/21/22/23) explicitly.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_conservative_trial.py`, porting the function 1:1 (drop `self`, take
   collaborators explicitly, including the three nested closures `_partial`/`_tp_cleared`/
   `_move_sl`).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_conservative_trial.py` (234 lines) as
`handle_conservative_trial(trade, tick, bridge, tp_cache, close_full_after_tps=None)`,
porting `_handle_conservative_trial` 1:1 including its three nested closures
(`_partial`/`_tp_cleared`/`_move_sl`), with `bridge`, `tp_cache`, and the
optional `close_full_after_tps` callable taken as explicit parameters (same
deferred-dependency pattern as packs 17/19/21/22/23). Reuses
`core_tp_trigger_tracking`'s `get_triggered_tps`/`get_remaining_lots`
(pack 5) and `core_partial_close.partial_close_trade` (pack 9).

010's 13 tests ported verbatim into
`tests/core/test_handle_conservative_trial_surface.py` -- import changes
only (`hct.handle_conservative_trial(trade, tick, bridge, TPCache())`
instead of `SimulationEngine._handle_conservative_trial(engine, trade, tick)`),
zero assertion changes. All 13 pass, including both non-obvious
characterization findings from 010 (the recurring `partial_close_trade`
TP1 BE-move, and the stale-in-memory-`trade`-dict cascade quirk on a
same-tick TP1+TP2 crossing).

Full `tests/core/` suite: 631 passed. Full repo `tests/` suite: 962 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- verified via the fake bridge's call log in both
the characterization and surface test files.
