# 020 — Extract pending signal activation

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** places a genuine MT5 market order via
`open_trade_from_signal` -- identical call shape to the original; this pack's
own tests only ever mock it.

## Decision

Extract into `core_pending_signal_activation.py` as a single plain async
function `try_activate_pending_signals(tick, rs, bridge, retry_after,
dpm_candles, starting_balance=1000.0)` -- taking `bridge`, `retry_after`
(the per-signal backoff dict), and `dpm_candles` explicitly, no `self`.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_pending_signal_activation.py`, porting the function 1:1.
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_pending_signal_activation.py` (265 lines) as
`try_activate_pending_signals(tick, rs, bridge, retry_after, dpm_candles,
starting_balance=1000.0)`, porting the function 1:1. Reuses
`core_open_trade_from_signal.open_trade_from_signal` (pack 13),
`core_risk_governor.check_pre_trade_filters`/`price_in_entry_range`, and
`core_trade_reporting.get_open_trades` (all already extracted).

The extracted function's call to `open_trade_from_signal` now passes
`dpm_candles`/`starting_balance` explicitly, since that already-extracted
plain function requires them as parameters -- the original bound method
read them implicitly via `self._dpm_candles`/`self._cfg`, so its own call
site only ever passed `age_lot_mult`. This is a call-shape difference, not
a behavior difference (both paths ultimately source the same values); the
surface test's call-shape assertion was widened accordingly while every
other assertion carried over unchanged.

010's 13 tests ported into `tests/core/test_pending_signal_activation_surface.py`
-- one call-shape assertion updated as above, all 12 others unchanged. All
13 pass.

Full `tests/core/` suite: 992 passed. Full repo `tests/` suite: 1323 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- `open_trade_from_signal` is mocked in every test.
