# 020 — Extract max TP hit checker + backfill

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none.

## Decision

Extract into `core_max_tp_hit.py` as `_tp_level_from_extreme` (ported
verbatim, private pure helper), `max_tp_checker_sweep(bridge)` (the
per-cycle sweep body only -- the `sleep(90)`/`while`/`sleep(300)` shell
stays in `engine.py`, same split as `_tp_safety_net_loop`/
`tp_safety_net_sweep`), and `backfill_max_tp_hit_corrected(bridge)` (ported
in full, including its own `sleep(120)` startup delay, since the original
has no loop wrapper at all).

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).

## What to do

1. Confirm 010's suite is green.
2. Create `core_max_tp_hit.py`, porting all three pieces 1:1.
3. Re-run 010's suite against the new functions -- zero assertion changes.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- 010's suite passes unmodified (assertions) against the new functions.
- `engine.py` untouched.
- No real or demo MT5 order placed, closed, or modified at any point.

## Notes

Created `forex_trader/core/core_max_tp_hit.py` (177 lines) with the three
pieces described above. `to_db_thread` (already existing in `database.py`)
is used for real, not faked, in `backfill_max_tp_hit_corrected` -- it's a
generic executor-submit helper, not order-placing infrastructure.

010's 14 tests ported verbatim into `tests/core/test_max_tp_hit_surface.py`
-- import changes only, zero assertion changes. All 14 pass.

Full `tests/core/` suite: 1070 passed, 4 failed. Full repo `tests/` suite:
1403 passed, 4 failed. The 4 failures are in
`tests/core/test_open_trade_characterization.py` /
`test_open_trade_surface.py` (`test_remote_forwarding_*`, a
`KeyError: 'executed_remotely'`) -- confirmed pre-existing and unrelated to
this pack: `git status` shows only this pack's new, untracked files (no
`core_open_trade.py` or its tests touched), and the failures reproduce
identically running those two files in isolation. Notably the 2
`pytest-asyncio`-missing failures documented in every prior pack's Notes are
no longer present in this run -- `pytest-asyncio` appears to now be
installed in the venv, unrelated to this pack's own changes.

`engine.py` untouched. No real or demo MT5 order placed, closed, or
modified at any point -- this pack's functions never call an order-placing
collaborator; verified via the fake bridge's call log across both test
files.
