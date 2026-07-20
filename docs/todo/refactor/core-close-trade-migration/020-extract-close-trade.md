# 020 — Extract close trade

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** `close_trade`/`close_all_ladder_legs` call `bridge.close_position` --
the extracted code is identical to the original in this respect (still calls the real bridge
interface when wired to a real one), but this pack's own tests only ever pass a fake.

## Decision

Extract into `core_close_trade.py`: `CloseTradeContext` (bundles `bridge`, `starting_balance`,
`tp_cache`, `scale_out_last_fail`, `tp_safety_net_last_alert`, `on_profit`,
`schedule_profit_sync`, `background_close_commentary` -- see README for why each is needed and
why it's not extracting those subsystems), then `get_trading_balance(bridge,
starting_balance)`, `close_trade(trade_id, reason, ctx)`, `record_close(trade_id, close_price,
reason, ctx)`, `close_all_ladder_legs(trade_id, row, legs, reason, ctx)`. Reuses
`core_fees_sizing.pnl()` (pack 1), `core_risk_governor.rg_apply_halts_on_close()` (pack 1),
`core_dpm_bookkeeping.finalize_dpm_record()` (pack 4) instead of `self.pnl()`/
`self._rg_apply_halts_on_close()`/`self._finalize_dpm_record()`.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, `SimulationEngine.__new__`
  instance + loose attributes swapped for a `CloseTradeContext`, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_close_trade.py`: the `CloseTradeContext` class, then the four functions,
   porting each 1:1 (drop `self`, thread `ctx` through instead).
3. Re-run 010's suite against the new functions -- zero assertion changes beyond the
   engine-instance -> `CloseTradeContext` swap.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_close_trade.py` (368 lines, well under the 800-line ceiling) --
`CloseTradeContext` class plus 1:1 ports of all 4 functions, no logic changes. Reuses
`core_fees_sizing.pnl()`, `core_risk_governor.rg_apply_halts_on_close()`, and
`core_dpm_bookkeeping.finalize_dpm_record()` directly rather than re-deriving that logic.
Added `tests/core/test_close_trade_surface.py` (18 tests, 010's exact assertions re-pointed at
the new module, the `SimulationEngine.__new__()` instance + loose attributes replaced by a
`CloseTradeContext`). Full `tests/core/` suite: 300/300 green (282 from packs 1-9 + 18 from
this pack). Repo-wide: 631/633 green -- same 2 pre-existing `pytest-asyncio`-missing failures
from earlier packs, unrelated. `engine.py` untouched -- new module not yet wired back in.

No real or demo MT5 order was placed, closed, or modified at any point in this pack -- every
`bridge.close_position` call across both the characterization and surface suites went to a
plain in-memory fake, and its call log was asserted against directly (not just inferred from
the absence of errors).
