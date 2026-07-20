# 020 — Extract fees, sizing, sim account, Risk Governor

**Status:** Done (2026-07-20)
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

Created `forex_trader/core/core_fees_sizing.py` (63 lines), `core_sim_account.py` (43 lines),
`core_risk_governor.py` (272 lines) — all 1:1 ports, well under the 800-line ceiling. Two
self-caught issues during extraction, both fixed before commit: a guessed import path
(`forex_trader.mt5_types` instead of the real `forex_trader.core.models` for
`CONTRACT_SIZE`/`POINT_SIZE`, found by grepping `engine.py`'s actual import block) and an
unnecessary `_contract_size()` indirection helper (replaced with a direct `CONTRACT_SIZE`
import, matching `core_fees_sizing.py`'s pattern). Also removed a stray
`_PENDING_ACTIVATION_BACKOFF_S` constant that had been carried over from `engine.py` by
proximity but belongs to `_try_activate_pending_signals`, which is out of scope here.

Added three new test files under `tests/core/` (`test_fees_sizing_surface.py`,
`test_sim_account_surface.py`, `test_risk_governor_surface.py`, 31 tests) — 010's exact
assertions re-pointed at the new module functions instead of `SimulationEngine`. Plus one new
test, `test_rg_apply_halts_on_close_is_now_atomic`, the mirror of 010's forced-failure proof:
same technique (patch `set_app_config` to raise on its 2nd call), but now asserts BOTH
`trade_pause_until` and `risk_halt_reason` are `None` after the crash — confirming the
`with db_module.db():` wrap actually closes the gap 010 proved was real.

Full suite: 82/82 green in `tests/core/`, 413/415 green repo-wide. The 2 failures
(`tests/test_signal/test_engine_characterization.py::test_close_signal_full_lifecycle_balance_math`
and `::test_close_signal_loss_reduces_balance`) are pre-existing and unrelated — the environment
is missing the `pytest-asyncio` plugin, so `@pytest.mark.asyncio` tests can't run at all
("async def functions are not natively supported"). Reproduces identically on a clean tree with
none of this pack's new files present; nothing to do with this extraction.
