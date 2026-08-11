# 060 — Money-path coverage floors

**Status:** not started
**Depends on:** phase2/010 (the ratchet must be fed before floors mean anything)
**Touches money:** no — tests only; no production code changes in this task
**Layer:** tools/tests
**Leverage:** `/coverage-gap` skill; the fed coverage artifact from phase2/010; existing MT5 fakes

## Problem

Review testing M5: the code that touches money is among the least tested — `services/broker` floor
is only 58.3%; `broker/mt5_native.py` and `trading/manual_limit_order.py` have **zero** test
references; and the hand-set absolute floors in `tests/refactor/test_coverage_gate.py` omit
broker/ and runtime.py entirely, so their coverage can silently collapse.

## Decision

Test the two zero-coverage modules first (characterization against fakes — pin what they do
today), raise `services/broker` toward a floor the owner accepts, then add broker/ and runtime.py
to the absolute floors at the achieved values. Floors only ever ratchet up.

## What must NOT change

- Production code: zero edits. If writing a test reveals a bug (likely, given phase 1's findings
  overlapped these modules), the bug is **reported to the owner and taskified** — never quietly
  fixed under a coverage task, and never enshrined by a test asserting the wrong behaviour;
  characterize with a `# KNOWN-ISSUE` marker + owner note instead.
- No existing floor lowered; no ratchet baseline moved down.

## Tests first (TDD)

This task *is* tests; the discipline inverts — each new test must be shown to fail when its
subject is perturbed (mutation spot-check per file):

- `tests/broker/test_mt5_native.py` — characterize request construction, retcode mapping, error
  paths against fakes; mutation check: flip a retcode mapping, tests fail
- `tests/trading/test_manual_limit_order.py` — sizing, validation, rejection paths; the manual
  path is a human-error surface — boundary-heavy
- `tests/refactor/test_coverage_gate.py` — add broker/ + runtime.py floors at achieved values;
  negative control: floor set above achieved fails the gate

## What to do

1. `/coverage-gap` on `services/broker`, `mt5_native.py`, `manual_limit_order.py`; record the
   per-file baseline numbers in PROGRESS.md.
2. Write the characterization/boundary tests; mutation spot-checks on each.
3. Raise floors; run the full checks.
4. Report any bugs found (expected: filling-mode and error-mapping issues near review risk H5) as
   proposed tasks for the owner.

## Where

- `tests/broker/`, `tests/trading/` — new tests
- `tests/refactor/test_coverage_gate.py` — floors

## Acceptance

- Zero-reference module count in the money path: 0. Broker floor ≥ agreed target (owner sets it —
  proposed: 80%). Floors include broker/ + runtime.py.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Owner decision on the broker floor target — proposed 80%, recorded in QUESTIONS if contested.
