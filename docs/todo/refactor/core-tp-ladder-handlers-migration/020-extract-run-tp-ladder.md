# 020 — Extract _run_tp_ladder (+ 3 wrappers)

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** partially closes and modifies a live order via
`bridge.partial_close`/`bridge.modify_order` -- identical call shape to the original; this
pack's own tests only ever pass a fake.

## Decision

Extract into `core_run_tp_ladder.py`: `run_tp_ladder(trade, tick, pcts_table, log_tag,
bridge, tp_cache, be_at_pos=0, close_full_after_tps=None)` plus three thin wrappers
(`handle_signal_climber`/`handle_gd_vip_runner`/`handle_adaptive_runner`) that call it with the
right table/`be_at_pos`. Reuses `core_tp_trigger_tracking.get_triggered_tps`/
`log_tp_wait_diagnostic`/`get_remaining_lots` (pack 5), `core_partial_close.partial_close_trade`
(pack 9), and pack 12's `_CLIMBER_PCTS`/`_GDVR_PCTS` (imported, not duplicated a third time).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_run_tp_ladder.py`, porting the shared engine + 3 wrappers 1:1 (drop `self`,
   take `bridge`/`tp_cache`/`close_full_after_tps` explicitly).
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_run_tp_ladder.py` (226 lines, well under the 800-line ceiling)
-- the shared engine plus all 3 wrappers, no logic changes once two self-caught bugs (below)
were fixed. Two real issues found and fixed during extraction, before either reached a commit:

1. **Wrong import source in the README/plan**: assumed `_CLIMBER_PCTS`/`_GDVR_PCTS` were
   already ported in pack 12's `core_signal_resolution.py` (that pack's README said so) --
   they weren't; pack 12's front half never needed the close-percentage tables, only the
   SL-distance constants. They WERE already ported in pack 11's `core_open_trade.py` (for the
   EA-ladder lookup), so imported from there instead of duplicating a third time. Caught
   immediately by an `ImportError` at test-collection time, before any test ran against wrong
   data.
2. **A real behavior-changing bug in my own first draft**: gated the unconditional `return`
   after `if res.get("auto_closed") and mt5_ticket:` behind `close_full_after_tps` also being
   truthy. The ORIGINAL always returns immediately in that branch — there's no "callback
   available or not" concept in the un-refactored code, `self._close_full_after_tps` is just
   always callable. My gating meant a caller that doesn't supply the (still out-of-scope)
   callback — every test in this pack's own suite — would wrongly fall through into the
   SL-trail block after a full auto-close, potentially moving SL on an already-closed
   position. Caught by a genuine test failure (`test_climber_tp3_last_closes_full_remaining_
   returns_before_sl_trail`), not by inspection — fixed by separating "should I return"
   (always, on auto-close) from "should I invoke the callback" (only if supplied). Re-checked
   pack 17's `core_handle_scale_out.py` for the same pattern — that handler's original has no
   `return` in this branch at all, so the equivalent gating there was harmless; only this
   pack's extraction had the bug.

Added `tests/core/test_run_tp_ladder_surface.py` (11 tests, 010's exact assertions re-pointed
at the new functions). Full `tests/core/` suite: 539/539 green (528 from packs 1-18 + 11 from
this pack). Repo-wide: 870/872 green -- same 2 pre-existing `pytest-asyncio`-missing failures
from earlier packs, unrelated. `engine.py` untouched -- new functions not yet wired back in. No
real or demo MT5 order was placed, closed, or modified at any point in this pack.
