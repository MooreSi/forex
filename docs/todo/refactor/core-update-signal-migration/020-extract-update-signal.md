# 020 — Extract update signal

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** modifies a live order via `bridge.modify_order`/`ea_bridge.update_trade`
-- identical call shape to the original; this pack's own tests only ever pass fakes.

## Decision

Extract into `core_update_signal.py` as a single plain async function taking `bridge`
explicitly. `ea_bridge` accessed the same module-level-singleton way as packs 11/13.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_update_signal.py`, porting the function 1:1 (drop `self`, take `bridge`
   explicitly).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order modified at any point.

## Notes

Created `forex_trader/core/core_update_signal.py` (172 lines) -- 1:1 port, no logic changes,
`bridge` taken explicitly, logging preserved verbatim. Added
`tests/core/test_update_signal_surface.py` (14 tests, 010's exact assertions re-pointed at the
new function). Full `tests/core/` suite: 474/474 green (460 from packs 1-14 + 14 from this
pack). Repo-wide: 805/807 green -- same 2 pre-existing `pytest-asyncio`-missing failures from
earlier packs, unrelated. `engine.py` untouched -- new function not yet wired back in.

No real or demo MT5 order was modified at any point in this pack -- every `bridge.modify_order`/
`ea.update_trade` call across both suites went to a plain in-memory fake, call logs asserted
directly. This closes out the entire trade-management cluster (packs 9-15): `partial_close_
trade`, `close_trade`/`_record_close`/`_close_all_ladder_legs`/`_get_trading_balance`,
`open_trade`, `open_trade_from_signal` (both halves), `open_manual_market_order`, and now
`update_signal`.
