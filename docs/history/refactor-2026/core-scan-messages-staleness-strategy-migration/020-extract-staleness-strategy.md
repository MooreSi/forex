# 020 — Extract staleness + strategy resolution

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_scan_messages_staleness_strategy.py` as two functions:
`record_staleness_or_new(tg_id, group_id, channel_name, msg, parsed,
source_label) -> bool` (True = fresh, proceed; False = stale, handled
here) and `resolve_strategy_and_skip_reason(rs, channel_name, text,
parsed, auto_execute, cfg_obj, engine_for_eval, is_trading_paused_fn) ->
dict` (bundles `strategy`/`strategy_name`/`skip_reason`/`sess_ok`/
`per_signal_skip`/`per_signal_skip_reason` -- sub-pack D's own scope needs
all of these). `engine_for_eval` is forwarded unchanged to
`channel_strategy_ai.evaluate_signal_strategy`, same "forward the engine
through" pattern as `core_gd_copy_research`. `is_trading_paused_fn` is a
required injected async callable.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions -- called directly instead
  of driving the whole `_scan_messages`, asserting on each function's
  return value instead of the captured `fmt_signal` call args (though
  `resolve_strategy_and_skip_reason`'s own return dict maps 1:1 onto what
  010 captured that way).

## What to do

1. Confirm 010's suite is green.
2. Create `core_scan_messages_staleness_strategy.py`, porting both blocks.
3. Re-run 010's suite (adapted per the decision above) against the new
   functions.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_scan_messages_staleness_strategy.py` (198
lines). 15 tests ported into
`tests/core/test_scan_messages_staleness_strategy_surface.py` -- same
scenarios as 010, called directly instead of via the whole
`_scan_messages` driver. All 15 pass.

Full `tests/core/` suite: 1257 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1590
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.

This completes sub-pack C of `core-scan-messages-migration`. Sub-pack D
(auto-execution -- the highest real-money-risk slice) remains.
