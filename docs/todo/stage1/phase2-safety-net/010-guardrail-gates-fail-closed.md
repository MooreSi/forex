# 010 — Guardrail gates: scan real paths, fail closed, feed the ratchet

**Status:** not started
**Depends on:** none (may run in parallel with phase 1)
**Touches money:** no
**Layer:** tools/tests
**Leverage:** the gate self-test negative-control doctrine already practiced in `tests/refactor/`

## Problem

The safety net has holes it cannot see (review testing H1/H2/H3):

- `tools/refactor_audit/orphan_detector.py:34` scans `forex_trader/core/`, deleted long ago —
  vacuously green on every run, wired into `tools/checks.py:51`. The exact failure CLAUDE.md
  documents as the reason these rules exist has recurred.
- `tools/checks.py:65` runs pytest without `--cov`; `.coverage.json` doesn't exist, so the
  coverage gate (`coverage_gate.py:24`) can't pass as documented — and would trust a stale file
  forever if one appeared.
- Every gate does `if not base.exists(): continue` — one rename from another silent gate.
- `pyproject.toml` names a nonexistent build backend (`setuptools.backends.legacy:build`) and
  omits ~12 runtime deps that requirements.txt declares.

## Decision

Repoint the orphan detector at `backend/src` + `frontend`, make **every** gate hard-fail on a
missing target path, add `--cov`+`--cov-report=json` to the checks suite run with a freshness check
on the artifact, and fix pyproject. Chosen over deleting the orphan gate because phase 3/010 (dead
code deletion) needs exactly this gate to prove deletions stay deleted.

## What must NOT change

- No ratchet baseline is *lowered*. If the repointed orphan gate or fed ratchet reveals violations
  (it will — the review counted ~2,800 dead lines), the gate ships with an explicit, dated
  **baseline file listing today's known offenders**, and phase 3 burns it down. New offenders fail.
- The four structural gates' existing rules stay as strict as they are.
- Test suite behaviour unchanged — only how it's invoked (`--cov`).

## Tests first (TDD)

- `tests/refactor/test_orphan_gate.py::test_orphan_detector_scans_existing_roots` — every
  configured root exists — structural
- `::test_planted_orphan_is_detected` — drop a temp module nothing imports into a scanned root →
  gate fails — the negative control that was missing for months — control
- `tests/refactor/test_gate_paths.py::test_all_gate_targets_exist` + `::test_missing_path_fails_gate`
  (planted rename) — every gate, not just orphan — structural + control
- `tests/refactor/test_coverage_feed.py::test_checks_invokes_cov` — the checks suite command line
  includes the cov flags — wiring
- `::test_stale_coverage_artifact_rejected` — artifact older than the run → gate fails — boundary
- `tests/tooling/test_pyproject.py::test_build_backend_importable` and
  `::test_runtime_deps_covered` (pyproject deps ⊇ requirements.txt) — structural

## What to do

1. Write the tests above; run them; confirm they fail for the right reason (several will fail
   against today's tree — that's the point; capture the output).
2. Repoint `orphan_detector.py` roots; generate the dated known-offenders baseline; wire new-offender
   detection to fail.
3. Sweep every gate under `tools/` for `exists(): continue` and convert to hard failure with a
   clear message naming the missing path.
4. Add `--cov --cov-report=json` to `tools/checks.py:65`; add the freshness check to
   `coverage_gate.py`.
5. Fix `pyproject.toml` backend (`setuptools.build_meta`) and reconcile deps with requirements.txt.
6. `python -m tools.checks all` — this task's Done requires the **whole** command honestly green.

## Where

- `tools/refactor_audit/orphan_detector.py`, `tools/checks.py`, `tools/**/coverage_gate.py` and
  sibling gates
- `pyproject.toml`

## Acceptance

- Planted orphan → red. Planted rename → red. Stale coverage artifact → red. Real tree → green.
  All four demonstrated with output pasted into PROGRESS.md.
- **The killer test:** `git stash` the fixes, run checks (vacuously green), pop, run again — the
  same tree now reports the true baseline. Green output has meaning again.

## Notes

- The known-offenders baseline is a *debt ledger*, not a licence — phase 3/010 must drain it to
  empty and then delete the baseline file.
- Do not silently add the ~12 missing pyproject deps if any look unused — cross-check against
  imports and flag genuinely unused requirements.txt entries instead of enshrining them.

## Progress notes (2026-08-10)

**Landed (tests-first, 12 tests green):**
- Coverage feed: `tools/checks.py` SUITE now runs `--cov=backend --cov=frontend
  --cov-report=json:.coverage.json`, and `_clear_stale_coverage()` deletes any leftover artifact
  before the suite so the gate only grades fresh data (fails closed with "no coverage data"
  otherwise). The path is imported from `coverage_gate.COVERAGE_JSON` so they can't drift.
  Tests: `tests/refactor/test_checks_feeds_coverage.py`.
- pyproject: build backend corrected `setuptools.backends.legacy:build` →
  `setuptools.build_meta`; dependencies reconciled to a superset of requirements.txt (all 13
  missing packages added, MetaTrader5 keeps its win32 marker). Tests:
  `tests/refactor/test_pyproject_metadata.py` (build backend importable; deps ⊇ requirements.txt).

**Still TODO (the orphan-detector redesign — bigger than a repoint):**
- `orphan_detector.py` cannot simply be "repointed". Its model is *public functions in
  `forex_trader/core/core_*.py` that nothing calls*. There are **no `core_*.py` files anywhere in
  the tree today**, so `find_orphans()` globs nothing and returns `[]` — vacuously green. And
  `tools/checks.py` invoked it **without `--check`**, so even its allowlist gate never ran.
- This codebase's real dead-code problem is orphan *modules* (phase3/010: three per-engine
  `database.py` clones + four orphan modules that nothing imports), which the function-level model
  would never catch anyway. The right fix is a **module-reachability** detector: from entrypoints
  (`run.py`, `backend.src.app`, `frontend.app`, `mt5_bridge.py`) walk the import graph and report
  unreached `backend/`+`frontend/` modules; curate the first run into a dated baseline.
- Watch for false positives: dynamically/framework-imported modules (NiceGUI page registration,
  the `-p tools.testing.fixed_clock` plugin, importlib/getattr dispatch). The baseline must
  distinguish "genuinely dead (phase3/010 deletes it)" from "reached dynamically (allowlist it)".
- This rewrites the existing `tests/refactor/test_orphan_detector.py` (which currently pins the
  obsolete `core_`-scoped behaviour) — a legitimate rewrite since the module it tests is being
  redesigned, but flag it explicitly in the commit per golden rule 4.
- Also still TODO from this task: make the structure/import-contract/facade gates fail **closed**
  when a target path is missing (they currently `continue`), and wire `orphan_detector --check`
  into `tools/checks.py`.

**Consequence for "honest green":** until the orphan redesign lands, `tools.checks all` may pass
but the orphan gate is still a rubber stamp — green is not yet fully honest. Do not call this task
Done until the redesign ships.
