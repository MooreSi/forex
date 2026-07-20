# 020 — Extract open trade from signal (back half)

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** places an order via `open_trade` and modifies it via
`bridge.modify_order`/`ea_bridge.update_trade` -- identical call shape to the original; this
pack's own tests only ever pass fakes.

## Decision

Extract into `core_open_trade_from_signal.py` as a single plain async function taking `bridge`
explicitly. Calls `core_signal_resolution.resolve_open_trade_params` (pack 12) then
`core_open_trade.open_trade` (pack 11). Reuses pack 12's `_gdvr_sl_dist`/`_adaptive_sl_dist`/
`_adaptive_final_tp_dist` and point-distance constants rather than duplicating them again.
`ea_bridge` accessed the same module-level-singleton way as pack 11. `background_open_
commentary` taken as an optional injected callable (default no-op), same pattern as pack 10.

## Tests first (TDD)

- 010's suite, re-pointed at the new function (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_open_trade_from_signal.py`, porting the back-half logic 1:1 (drop `self`, take
   `bridge` explicitly, recompute the entry-mid fallback values fresh from `sig` instead of
   reusing front-half locals that pack 12's function doesn't return).
3. Re-run 010's suite against the new function -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed or modified at any point.

## Notes

Created `forex_trader/core/core_open_trade_from_signal.py` (317 lines, well under the 800-line
ceiling) -- 1:1 port, no logic changes, including the original's `log.warning`/`log.info`
calls (initially dropped for brevity in the first draft, then restored to match every prior
pack's verbatim-port discipline). Reuses pack 11's `open_trade`, pack 12's
`resolve_open_trade_params`/`_gdvr_sl_dist`/`_adaptive_sl_dist`/`_adaptive_final_tp_dist`/
point-distance constants. `background_open_commentary` taken as an optional injected callable.

Added `tests/core/test_open_trade_from_signal_surface.py` (13 tests, 010's exact assertions
re-pointed at the new module). Full `tests/core/` suite: 422/422 green (409 from packs 1-12 +
13 from this pack). Repo-wide: 753/755 green -- same 2 pre-existing `pytest-asyncio`-missing
failures from earlier packs, unrelated. `engine.py` untouched -- new function not yet wired
back in.

No real or demo MT5 order was placed or modified at any point in this pack -- every
`bridge.place_order`/`modify_order`/`ea.update_trade` call across both suites went to a plain
in-memory fake, call logs asserted directly. This completes the `open_trade_from_signal` split
(packs 12+13) and, with it, the entire lowest-level trade open/close primitive layer
(`open_trade`, `close_trade`, `partial_close_trade`, `open_trade_from_signal`).
