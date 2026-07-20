# 020 — Extract _process_instant_entry

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** places a genuine MT5 market order via `open_trade` --
identical call shape to the original; this pack's own tests only ever mock
`open_trade` itself.

## Decision

Extract into `core_instant_entry.py` as a single plain async function
`process_instant_entry(msg, tg_id, group_id, channel_name, text, direction,
price, rs, auto_execute, bridge, dpm_candles, get_trading_balance_fn,
get_open_trades_fn)` -- taking `bridge` and the collaborators it needs
explicitly, no `self`. Calls `core_open_trade.open_trade` directly (already
extracted, pack 11) rather than through an injected callable, since it's a
direct, always-needed dependency (not a deferred/optional one).

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_instant_entry.py`, porting the function 1:1.
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_instant_entry.py` (400 lines) as
`process_instant_entry(msg, tg_id, group_id, channel_name, text, direction,
price, rs, auto_execute, bridge, dpm_candles, starting_balance=1000.0)`,
porting `_process_instant_entry` 1:1. Calls `core_open_trade.open_trade`
(pack 11) directly rather than through an injected callable, since it's a
direct, always-needed dependency, not a deferred one. Reuses
`core_close_trade.get_trading_balance` (pack 10) and
`core_trade_reporting.get_open_trades` (already extracted). Re-declares the
Conservative/Scalp Runner point constants locally (same convention as
packs 22/23 -- each pack re-declares the small constants it needs rather
than importing across sibling modules).

010's 19 tests ported verbatim into `tests/core/test_instant_entry_surface.py`
-- import changes only (module-level `open_trade`/`get_trading_balance`/
`get_open_trades` patched via `mock.patch.object(core_instant_entry, ...)`
instead of `SimulationEngine` methods), zero assertion changes. All 19 pass.

Full `tests/core/` suite: 797 passed. Full repo `tests/` suite: 1128 passed,
2 failed -- the same pre-existing `pytest-asyncio`-missing failures seen in
every prior pack, no new failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- `open_trade` is mocked in every test, never given
a real bridge to act through.
