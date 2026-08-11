# 020 — Add broker + runtime.py to the money-critical floors

**Status:** not started · **Touches money:** no (tests/gate config) · **Layer:** tools/tests

## Problem

`services/broker` (58.3%) and `runtime.py` (72.2%) are in the coverage gate's CRITICAL set but are
NOT in the hand-set absolute floors, so either can be baselined downward and still pass — the money
path's least-covered code has the weakest guard.

## Tests first (TDD)

- `tests/refactor/test_coverage_gate.py::test_broker_and_runtime_have_absolute_floors` — both appear
  in `MONEY_CRITICAL_FLOORS` at ≥ their current measured value — structural
- `::test_floor_below_actual_fails` — negative control: a floor set above actual fails the gate — control

## What to do

1. Write the tests; watch them fail.
2. Add `backend/src/services/broker` and `backend/src/runtime.py` to `MONEY_CRITICAL_FLOORS` at their
   current achieved values (do not invent higher numbers here; raising coverage is phase-3 follow-up /
   review-august-08 phase3/060). No existing floor lowered.
3. `python -m tools.checks all`.

## Where
- `tests/refactor/test_coverage_gate.py` (the absolute floors) · possibly `coverage_gate.py`.

## Acceptance
- broker + runtime carry absolute floors that can't silently fall; negative control demonstrated.
  Green suite.
