# 050 — Backtest, config & stragglers

**Status:** not started
**Depends on:** 010, 020, 030, 040 — this task sweeps whatever they left
**Touches money:** no. Backtesting runs against historical data and places nothing. **Confirm before relying on this:** verify `services/backtest/engine` has no live-broker path at all; if it does, stop and re-scope this task as money-touching.
**Layer:** frontend → controller
**Leverage:** nothing yet — backtest has no controller

## Problem

What tasks 010–040 do not claim:

| File | Line | Import |
|---|---|---|
| `frontend/pages/backtest.py` | 18 | `services.backtest.engine as bt` |
| `frontend/pages/backtest.py` | 321 | `services.backtest.engine._BROKER_TZ_OFFSET` — a **private** module constant |
| `frontend/pages/reversal_panel.py` | 25 | `reversal_engine_service` (if 010 left it) |
| various | — | anything 010–040 missed |

`backtest.py:321` reaching for `_BROKER_TZ_OFFSET` is the worst single line in the frontend: a page
reading a private constant out of a service module. The underscore is the service saying "this is
mine", and the page took it anyway. Whatever that offset means, the page needs it *as an answer*, not
as a constant — so the service should expose a function that uses it, and the page should never see
the number.

## Decision

- **New `backtest_controller.py`** — run a backtest, read its results, and whatever
  `_BROKER_TZ_OFFSET` is actually being used *for* at the call site, expressed as a named service
  function.
- Then sweep: run the contract check, and route whatever is left.

Read `backtest.py:321` in context before designing the function. If the page is converting a
timestamp, the service exposes the conversion, not the offset. Re-exporting the constant through a
controller would satisfy the contract while leaving the leak exactly where it is — that is the
failure mode this whole phase exists to prevent, and it would be worse than leaving the line alone.

## What must NOT change

- **Backtest results.** The same inputs produce identical output: same trades, same P&L, same
  equity curve. A backtest that changes its answer during a restructure is a backtest nobody can
  trust again.
- Broker timezone handling. Whatever `_BROKER_TZ_OFFSET` compensates for, it still compensates for it
  identically — this is exactly the kind of constant that silently shifts a candle boundary.
- Backtests remain incapable of touching a live or demo account.
- Existing tests in `tests/services/` for backtest pass unmodified except mock-target relocations.

## Tests first (TDD)

- `tests/services/test_backtest_characterization.py::test_a_fixed_dataset_produces_the_same_result`
  — characterization against a pinned input dataset, asserting trade count, total P&L and final
  equity to exact values. Written **before** anything moves. This is the safety net for the
  timezone-offset change.
- `tests/services/test_backtest_characterization.py::test_the_pinned_result_can_fail`
  — **negative control**. Shift the offset by an hour in a copy and assert the characterization
  notices. This one earns its keep: if it does not fail, the test is not seeing the offset at all.
- `tests/controllers/test_backtest_controller.py::test_run_forwards_to_the_service` — surface.
- `tests/controllers/test_backtest_controller.py::test_the_controller_exposes_no_private_constant`
  — structural. Asserts no name starting with `_` is re-exported. Pins the decision above so a
  future session cannot quietly take the easy route.
- `tests/refactor/test_frontend_service_boundary.py::test_no_frontend_file_imports_a_service`
  — the sweep, as a test rather than a manual check.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason (characterization passes,
   the rest fail).
2. **Read `backtest.py:321` in full context.** Work out what the offset is being used for and design
   the service function around the question, not the constant. Write down what you found in
   PROGRESS.md — it is the kind of thing nobody will reconstruct later.
3. Add the named function to `services/backtest/`.
4. Create `backend/src/controllers/backtest_controller.py`.
5. Rewire `backtest.py`, both sites.
6. Run `python -m tools.refactor_audit.import_contracts --check`. Route whatever remains, one file
   per commit.
7. `python -m tools.checks all`.

## Where

- `backend/src/services/backtest/` — a named function replacing the private-constant read
- `backend/src/controllers/backtest_controller.py` — **new**
- `frontend/pages/backtest.py:18, 321`
- whatever the sweep turns up

## Acceptance

- `import_contracts --check` reports `frontend-reaches-the-backend-through-controllers: 0`.
- No frontend file references any underscore-prefixed name from a service module.
- **The killer test:** run the same backtest over the same date range before and after — identical
  trade count, identical total P&L, identical equity curve. Paste both results into PROGRESS.md
  side by side.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- The count reaching 0 here is what unblocks task 060. Do not update any baseline in this task —
  060 owns that.
- If the sweep turns up a call site that genuinely has no sensible controller home, do not force one.
  Leave it, record it in PROGRESS.md with the reason, and raise it with the owner — 060 then has to
  decide between an `allowed` entry and leaving the contract baselined at a small number. An honest
  1 with a written reason beats a 0 bought with a re-export.
