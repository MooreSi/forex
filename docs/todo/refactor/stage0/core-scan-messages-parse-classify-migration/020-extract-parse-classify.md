# 020 — Extract parse/classify block

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_scan_messages_parse_classify.py` as
`classify_and_parse(tg_id, group_id, channel_name, text, msg, parser_fmt,
sig_prefix, ai_fallback_fn, queue_unrecognised_fn)`, returning the parsed
signal dict or `None` (fully handled here). `ai_fallback_fn`/
`queue_unrecognised_fn` are required explicit collaborators, same
"caller binds the simplified shape" pattern as sub-pack A's
`close_trade_fn`.

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- called directly instead
  of driving the whole `_scan_messages`, asserting on the returned
  `parsed` dict (or `None`) instead of the `new_signals` list. One
  self-caught test bug fixed: `sig_prefix=""` in the `auto`-format test
  doesn't reproduce real behavior, since the real caller always resolves
  `sig_prefix = ch_cfg.get('signal_prefix') or SIGNAL_PREFIX` before this
  block runs -- it's never actually empty by the time `classify_and_parse`
  sees it. Fixed by passing `SIGNAL_PREFIX` explicitly, matching what the
  real caller would supply.

## What to do

1. Confirm 010's suite is green.
2. Create `core_scan_messages_parse_classify.py`, porting the block 1:1.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_scan_messages_parse_classify.py` (233
lines). 19 tests ported into
`tests/core/test_scan_messages_parse_classify_surface.py` -- same
scenarios as 010, called directly instead of via the whole
`_scan_messages` driver. All 19 pass after the `sig_prefix` fix above.

Full `tests/core/` suite: 1227 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1560
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.

This completes sub-pack B of `core-scan-messages-migration`. Sub-packs
C (staleness + strategy resolution) and D (auto-execution) remain.
