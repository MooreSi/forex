# 010 — Delete the dead code, drain the orphan baseline

**Status:** not started
**Depends on:** phase2/010 (the repointed orphan gate is the proof mechanism)
**Touches money:** no — deletions only, of code with zero production imports
**Layer:** service
**Leverage:** phase2/010's dated known-offenders baseline is the worklist

## Problem

~2,800 dead lines (review backend Critical #4): three per-engine `database.py` files (~2,171
lines, zero production imports, ~90% clones of the live `*_repo.py` modules) plus four orphaned
modules. Dead near-clones of live repo code are worse than clutter — a future session can edit the
dead copy and believe the change landed. This is precisely the failure mode from the project's
previous audit.

## Decision

Delete, don't archive (git history is the archive). Every deletion is proved twice: the orphan
gate stops listing it in the baseline, and the full suite stays green. Work engine by engine, one
commit per engine, so a surprise reference bisects trivially.

## What must NOT change

- Behaviour: zero. If deleting a "dead" module breaks anything, it wasn't dead — stop, restore,
  and record the real importer in the baseline notes for investigation.
- The live `*_repo.py` modules — byte-identical; only their dead clones die.
- `docs/history/` untouched.

## Tests first (TDD)

- For each candidate, before deleting: `python -c "import <module>"` inventory + grep for the
  module name across backend/frontend/tests/tools (including string-based imports) — recorded in
  the commit message as evidence, not guessed.
- `tests/refactor/test_orphan_gate.py::test_baseline_is_empty` — flips from failing to green as
  the ledger drains; ends this task — structural
- Negative control: re-plant one deleted module from git, assert the orphan gate flags it — control
- The full suite is the regression net; no new behaviour tests (nothing should behave differently).

## What to do

1. Take the phase2/010 baseline as the worklist; verify each entry's zero-import status freshly.
2. Delete the three per-engine `database.py` clones (one commit each), then the four orphan
   modules.
3. After each commit: `python -m tools.checks all` — suite + gates + boot.
4. Delete the baseline file itself; the orphan gate now runs at zero tolerance.
5. Grep tests/ for tests that only exercised deleted modules; delete those with the module (a test
   of dead code is dead code) — flagged per-file in the commit message.

## Where

- the three engine `database.py` files (paths in the phase2/010 baseline)
- four orphan modules (ditto)

## Acceptance

- `wc -l` delta ≈ −2,800; orphan gate at zero with no baseline; suite green.
- **The killer test:** the re-plant negative control — the gate that missed this for months now
  catches a planted orphan within one run.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Progress notes (2026-08-10) — investigation before deletion

A module-reachability detector (`tools/refactor_audit/orphan_modules.py`, built in phase2/010)
found **7 unreached modules, 2,813 LOC** — matching the review's ~2,800. But investigating each
before deleting revealed **"nothing imports it" has two causes needing opposite fixes**, so the
blanket "delete all 7" is wrong:

**Confirmed superseded-dead (delete — but test-entangled, do deliberately):**
- `reversal_engine/database.py` (752), `test_signal/database.py` (721),
  `breakout_signal/database.py` (698) — the three per-engine clones, superseded by their
  `*_repo.py`. Zero prod imports. Deleting each requires also: removing its dedicated
  `test_database_characterization.py` (a dead-code test), removing stale entries from
  `tests/refactor/test_transaction_boundaries.py`, and (breakout only) removing the **vestigial**
  `_legacy_bo_db` fixture in `tests/breakout_signal/test_engine_characterization.py` — whose comment
  claiming `ml_engine.record_outcome` still uses the legacy module is **STALE** (it uses
  `breakout_signal_repo` now; verified 2026-08-10).

**NOT clearly dead — built-but-unwired, OWNER decision (do NOT delete mechanically):**
- `channels/rule_generator.py` (275) — auto rule-gen the user "explicitly chose"; codebase
  references a differently-named `ai_rule_generator.py`. Verify which is live.
- `breakout_signal/backtest.py` (226) — walk-forward pre-live validation harness, documented for
  manual invocation; likely a dev tool, not dead.
- `config/licence/client.py` (90) — licence/auth-server HTTP client with cert pinning; dormant
  security infra, ties to phase4/030.
- `test_signal/auth.py` (51) — test-module password protection; appears disconnected.

Full per-module classification + reasons live in
`tools/refactor_audit/orphan_module_allowlist.json`. **Deletion is paused pending owner decisions
on the four unwired modules** (wire vs remove) and a deliberate pass on the three test-entangled
clones. Nothing was deleted on 2026-08-10.

## Notes

- If any clone has silently *diverged* from its live repo (the review says ~90% identical), diff
  before deleting and check whether the divergence is an unshipped fix someone made in the wrong
  file — surface any such finding to the owner before the delete.
