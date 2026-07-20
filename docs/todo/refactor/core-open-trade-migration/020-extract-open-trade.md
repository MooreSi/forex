# 020 — Extract open trade

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** places an order via `bridge.place_order` or the EA bridge -- identical
call shape to the original; this pack's own tests only ever pass fakes.

## Decision

Extract into `core_open_trade.py` as a single plain async function taking `bridge` explicitly
instead of `self._bridge`/`self.get_fresh_tick()`. `ea_bridge`, `sync.server`, `sync.client`,
`db_module`, and `core_risk_governor.is_trading_paused` (pack 1) are imported and used directly
-- no new context/state carrier needed (see README for why). Also ports the
`_EA_LADDER_PCTS`/`_EA_LADDER_BE_AT_POS`/`_CLIMBER_PCTS`/`_GDVR_PCTS` static lookup tables
verbatim.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_open_trade.py`, porting `open_trade` 1:1 (drop `self`, take `bridge`
   explicitly, call `core_risk_governor.is_trading_paused` instead of `self.is_trading_paused`).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order (Python bridge or EA) placed at any point.

## Notes

Created `forex_trader/core/core_open_trade.py` (305 lines, well under the 800-line ceiling) --
1:1 port, no logic changes. Takes `bridge` explicitly; `ea_bridge`/`sync.server`/`sync.client`
imported and called directly, same as the original (already module-level singletons, no new
context class needed, unlike pack 10's `CloseTradeContext`). Reuses pack 1's
`core_risk_governor.is_trading_paused`. Ported `_EA_LADDER_PCTS`/`_EA_LADDER_BE_AT_POS`/
`_CLIMBER_PCTS`/`_GDVR_PCTS` verbatim, importing the real `STRATEGY_*` constants (not hardcoded
string literals) for the lookup table keys.

Added `tests/core/test_open_trade_surface.py` (15 tests, 010's exact assertions re-pointed at
the new function). Full `tests/core/` suite: 330/330 green (300 from packs 1-10 + 15 from this
pack, both 010 and 020's test files counted). Repo-wide: 661/663 green -- same 2 pre-existing
`pytest-asyncio`-missing failures from earlier packs, unrelated. `engine.py` untouched -- new
function not yet wired back in.

No real or demo MT5 order (Python bridge or EA) was placed at any point in this pack -- every
`bridge.place_order`/`ea.open_trade` call across both suites went to a plain in-memory fake,
call logs asserted directly.
