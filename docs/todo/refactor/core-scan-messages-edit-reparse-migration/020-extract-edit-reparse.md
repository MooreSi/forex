# 020 — Extract edit/re-parse state machine

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** the instant-entry-flip-flatten branch calls
`close_trade_fn` on a real open position -- faked in every test here.

## Decision

Extract into `core_scan_messages_edit_reparse.py` as
`handle_signal_edit(tg_id, group_id, channel_name, text, parser_fmt,
existing, ai_fallback_fn, find_and_apply_instant_followup_fn,
close_trade_fn)`, returning `None` (fully handled, caller moves to the
next message) or the parsed signal dict (promotes to the normal execution
flow). `existing` is the same 5-column row dict
(`id, direction, status, raw_text, entry_low`) the original code fetches.
The three collaborators are required explicit parameters bound to the same
simplified call shape `_scan_messages` itself uses -- their real
underlying implementations need additional context (cfg, bridge,
is_active_trader_node, a `CloseTradeContext`) only the caller has, so no
real default is supplied here.

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- `existing` fetched via
  the same 5-column query instead of driving the whole `_scan_messages`,
  collaborators passed as plain closures instead of mocked on the class.
  One assertion added (`test_full_reparse_same_direction_pending_followup_promotes`
  now also asserts the returned dict's `direction`, since the surface
  function's return value directly carries the "promote" signal that 010
  could only observe indirectly via the DB row after driving the whole
  method).

## What to do

1. Confirm 010's suite is green.
2. Create `core_scan_messages_edit_reparse.py`, porting the block 1:1.
3. Re-run 010's suite (adapted per the decision above) against the new
   function.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- Adapted 010 suite passes against the new function.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point --
  `close_trade_fn` is always faked.

## Notes

Created `forex_trader/core/core_scan_messages_edit_reparse.py` (243
lines). 12 tests ported into
`tests/core/test_scan_messages_edit_reparse_surface.py` -- same scenarios
as 010, called directly instead of via the whole `_scan_messages` driver.
All 12 pass.

Full `tests/core/` suite: 1189 passed, 4 failed (the same pre-existing,
unrelated `test_open_trade_*` failures noted since
`core-max-tp-hit-migration`'s 020 doc). Full repo `tests/` suite: 1522
passed, 4 failed, same failures.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point.

This completes sub-pack A of `core-scan-messages-migration`. Sub-packs
B (parse/classify), C (staleness + strategy resolution), and D
(auto-execution) remain.
