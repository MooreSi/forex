# 020 — Extract auto-execution flow

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** highest in the whole migration series -- places a
real MT5 order via `open_trade`; every test here fakes it.

## Decision

Extract into `core_scan_messages_auto_execute.py` as
`execute_auto_signal(parsed, tg_id, channel_name, source_label, strategy,
rs, sess_ok, per_signal_skip, per_signal_skip_reason, skip_reason, bridge,
get_open_trades_fn, find_and_apply_instant_followup_fn,
check_pre_trade_filters_fn, suggest_lot_size_fn, get_trading_balance_fn,
open_trade_fn=None)`, returning `{'executed', 'exec_lot', 'exec_price',
'trade_result', 'skip_reason', 'gap_note'}` plus an optional
`'deferred_stood_down': True` marker on the one path that needs to signal
"skip the final alert AND stop here" to the (not-yet-written) caller,
matching the original's own early `continue` in that branch.
`price_in_entry_range` (the small pure `@staticmethod`) is ported
verbatim. `open_trade_fn` defaults to the real, already-extracted
`core_open_trade.open_trade`; every other collaborator is a required
explicit parameter per the parent scoping doc's decision on small/
already-extracted unextracted helpers.

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- called directly with a
  fake bridge and a full set of injected collaborators instead of driving
  the whole `_scan_messages`; assertions on the returned dict/DB state
  instead of `new_signals`/captured alert calls. One self-caught test bug
  fixed in 010 (the IME-follow-up test needed
  `immediate_market_entry=1` in risk settings to actually reach the
  follow-up dispatch gate) carried forward correctly here since the
  surface test takes the risk-settings dict directly.

## What to do

1. Confirm 010's suite is green.
2. Create `core_scan_messages_auto_execute.py`, porting the block 1:1.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point --
  `open_trade_fn` and `bridge.modify_order` are always faked.

## Notes

Created `forex_trader/core/core_scan_messages_auto_execute.py` (327
lines) -- the largest single extraction module in this entire migration
series, matching the size and density of the original block. 15 tests
ported into `tests/core/test_scan_messages_auto_execute_surface.py` --
same scenarios as 010, called directly instead of via the whole
`_scan_messages` driver. All 15 pass.

Full `tests/core/` suite: 1287 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1620
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.

**This completes sub-pack D and the entire `core-scan-messages-migration`
project (sub-packs A-D), and with it the entire `core/engine.py`
migration series.** Every genuinely-computational piece of the original
10,065-line monolith has now either been extracted into a small, tested
`forex_trader/core/core_*.py` module, or deliberately left in place as
pure dispatch/orchestration (documented in each relevant pack's own
Notes). `engine.py` itself remains completely untouched throughout --
every new module exists standalone and tested, not yet wired back in,
consistent with every prior pack's precedent. Rewiring `engine.py` to
call the extracted modules is a distinct, future decision, not part of
this characterize-and-extract effort.
