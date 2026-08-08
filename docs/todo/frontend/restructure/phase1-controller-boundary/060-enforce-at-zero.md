# 060 — Flip the contract to enforced-at-zero

**Status:** not started
**Depends on:** 050 (the count must actually be 0 first)
**Touches money:** no — tooling only, no runtime code changes.
**Layer:** tools/tests
**Leverage:** `tools/refactor_audit/import_contracts.py` — the whole mechanism exists; this flips one flag

## Problem

A baselined contract at 0 and a contract enforced at 0 are not the same thing. The first records that
nobody has added a violation *yet*; the second makes adding one fail the suite. Until the flag flips,
the next page that imports a service directly sails through, and the 59 → 0 work quietly begins
reversing.

The module's own docstring makes the distinction and the stakes: *"a contract that is green only
because it was written to be green is worse than no contract: it certifies a boundary nobody is
holding."*

## Decision

Set `enforced_at_zero=True` on `frontend-reaches-the-backend-through-controllers`, remove its key
from `import_contracts_baseline.json`, and update the rationale — it currently ends "Shrinks as pages
are drained; see FINISH_LINE.md", which stops being true the moment this lands.

Then prove the flipped contract can actually fail. A gate that cannot detect the thing it forbids is
this repo's signature failure — the deleted-directory scanner that printed "all good" for months.

## What must NOT change

- The other six contracts: their flags, baselines and rationales are untouched.
- `--check` / `--update-baseline` interface unchanged.
- No runtime code changes at all. If this task needs to edit anything under `frontend/` or
  `backend/`, the count was not really 0 and task 050 is not finished.
- The existing test asserting each rationale is more than a restatement of its rule must still pass
  against the rewritten rationale — so write a real reason, not "the frontend must reach the backend
  through controllers".

## Tests first (TDD)

- `tests/refactor/test_import_contracts.py::test_frontend_service_contract_is_enforced_at_zero`
  — structural. Asserts the flag is `True` and the baseline has no key for it.
- `tests/refactor/test_import_contracts.py::test_the_contract_detects_a_planted_frontend_service_import`
  — **the negative control that matters most in this pack.** Write a temp file under `frontend/`
  containing `from backend.src.services.risk import settings`, run the checker, assert it reports a
  violation, then clean up. Without this the flag is a claim, not a guarantee.
- `tests/refactor/test_import_contracts.py::test_the_contract_still_allows_controller_imports`
  — the other half: a planted `from backend.src.controllers import trading_controller` must **not**
  be flagged. A gate that rejects everything is as useless as one that rejects nothing.

## What to do

1. Confirm the count is genuinely 0: `python -m tools.refactor_audit.import_contracts --check`.
   Do not proceed on a remembered number — run it.
2. Write the three tests. Run them. The first two fail (flag not set), the third passes.
3. Set `enforced_at_zero=True` on the contract.
4. Delete `"frontend-reaches-the-backend-through-controllers"` from
   `import_contracts_baseline.json`.
5. Rewrite the rationale: what the boundary buys and what breaks without it, in the register the
   other six use. Say that it was drained from 99 → 59 → 0 and when.
6. Run the three tests; all pass.
7. `python -m tools.checks all`.

## Where

- `tools/refactor_audit/import_contracts.py` — the flag and the rationale
- `tools/refactor_audit/import_contracts_baseline.json` — one key removed
- `tests/refactor/test_import_contracts.py` — three tests

## Acceptance

- `--check` prints `frontend-reaches-the-backend-through-controllers: enforced at zero`, alongside
  the four that already say it.
- A planted service import in a frontend file **fails** the check — demonstrated by a test, not by
  assertion.
- A controller import is still allowed.
- Baseline file has three keys left: `no-nicegui-in-the-backend`,
  `utils-and-config-depend-on-nothing-above-them`, and nothing else.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- If task 050 left an honest exception, this task decides how to hold it: an explicit `allowed`
  prefix with a comment saying why, or the contract stays baselined at that small number. Do **not**
  flip the flag with a violation outstanding, and do not delete the violation by widening `forbidden`
  until it no longer sees it.
- This is the task that makes the phase permanent. Everything before it is reversible drift; after
  it, the boundary holds itself.
