# 020 — Extract _handle_conservative

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- identical call shape to the original; this
pack's own tests only ever pass a fake.

## Decision

Extract into `core_handle_conservative.py` as a single plain async function taking `bridge`, a
`TPCache` (pack 5), and `close_full_after_tps` (optional injected callable) explicitly.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_handle_conservative.py`, porting the function 1:1 (drop `self`, take
   collaborators explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_handle_conservative.py` (166 lines) as
`handle_conservative(trade, tick, bridge, tp_cache, close_full_after_tps=None)`,
porting `_handle_conservative` 1:1 with `bridge`, `tp_cache`, and the optional
`close_full_after_tps` callable taken as explicit parameters (same deferred-
dependency pattern as packs 17/19/21). Reuses `core_tp_trigger_tracking`'s
`get_triggered_tps`/`log_tp_wait_diagnostic`/`get_remaining_lots` (pack 5) and
`core_partial_close.partial_close_trade` (pack 9).

010's 8 tests ported verbatim into
`tests/core/test_handle_conservative_surface.py` -- import changes only
(`hc.handle_conservative(trade, tick, bridge, TPCache())` instead of
`SimulationEngine._handle_conservative(engine, trade, tick)`), zero
assertion changes. All 8 pass, including the SL-breakeven-via-
`partial_close_trade` characterization discovery from 010.

Full `tests/core/` suite: 585 passed. Full repo `tests/` suite: 916 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack (`test_close_signal_full_lifecycle_balance_math`,
`test_close_signal_loss_reduces_balance`), no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified -- verified via the fake bridge's call log in both the
characterization and surface test files.
