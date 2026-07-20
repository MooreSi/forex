# 020 — Extract fees, sizing, sim account, Risk Governor

**Status:** not started
**Depends on:** 010
**Real-money surface:** no

## Decision

Extract as plain functions (not mixins — none of the target methods use `self`) into
`core_fees_sizing.py`, `core_sim_account.py`, `core_risk_governor.py`, calling `db_module`
directly (no parallel repo, see README). Fix `_rg_apply_halts_on_close`'s atomicity gap by
wrapping its body in `with db_module.db():` — the existing re-entrant `db()` makes the two
inner `set_app_config()` calls participate in one transaction automatically, no new
infrastructure needed.

## Tests first (TDD)

- 010's suite, re-pointed at the new functions (import changes only, same assertions).
- A new test proving the fixed `_rg_apply_halts_on_close` rolls back BOTH config writes
  together on a forced failure (mirrors the other packs' atomicity proofs).

## What to do

1. Confirm 010's suite is green.
2. Create the three new files, porting each function 1:1 (drop `self`, take explicit params
   instead of reading instance state).
3. Fix the one atomicity gap.
4. Re-run 010's suite against the new functions — zero assertion changes.
5. Add the new atomicity proof test.
6. Leave `engine.py` untouched — same precedent as the engine packs.

## Acceptance

- 010's suite passes unmodified against the new functions.
- Atomicity proven for `rg_apply_halts_on_close`.
- `engine.py` untouched.

## Notes

This does NOT wire the new functions back into `SimulationEngine` — `engine.py`'s own methods
still call their original inline logic. Wiring is separate, later work, same as the engine
packs' precedent of leaving old files in place until an explicit cutover decision.
