# 010 — One CI job: tools.checks all, every push

**Status:** **done (2026-08-10)** — `.github/workflows/checks.yml` runs `tools.checks all` on Windows on every push/PR. Header was stale; audited 2026-09-02.
**Depends on:** phase2/010 (an honest gate suite)
**Touches money:** no
**Layer:** tools/tests
**Leverage:** `python -m tools.checks all` already is the single entry point — CI just runs it

## Problem

Review testing M4: no CI, no hooks — every gate is a voluntary local command. The project's
history (a guardrail dead for months) shows exactly what voluntary verification decays into.

## Decision

One workflow (GitHub Actions if the repo gets a GitHub remote; the repo at c:\dev\forex is not
currently a git repo at the top level — see Notes) running `python -m tools.checks all` on every
push and PR, Windows runner to match production, MetaTrader5 import faked exactly as the local
suite does. No matrix, no lint stack, no second opinion — the local command *is* the contract;
CI's only job is running it when humans forget.

## What must NOT change

- The checks command stays the single source of truth — CI adds **no** checks of its own, so local
  green and CI green can never disagree by construction.
- Suite behaviour: CLAUDE.md warns two concurrent suites produce phantom failures — CI must set
  concurrency: one run per ref, and never run while a self-hosted runner shares state (use
  ephemeral runners).

## Tests first (TDD)

- N/A in the pytest sense; the verification is operational:
  - a push with a planted failing test → red run (the negative control)
  - a push of a clean tree → green run
  - both linked in PROGRESS.md

## What to do

1. Resolve the git question in Notes with the owner (blocking).
2. Author the workflow: checkout, Python per pyproject, `pip install -r requirements.txt`,
   `python -m tools.checks all`, artifact-upload the checks output.
3. Plant a failing test on a branch; prove red. Revert; prove green.
4. Branch protection: checks required before merge to the default branch.

## Where

- `.github/workflows/checks.yml` (or the equivalent for the chosen host)

## Acceptance

- The planted-failure run is red, the clean run is green, both by link; merges to the default
  branch require the check.

## Notes

- **Blocking owner decision:** `c:\dev\forex` is not a git repository at its root (only content
  under it). Where does version control actually live for `app/`, and is there a remote? If none:
  first step is `git init` + a remote, which is its own small conversation about what gets
  committed (config.yaml, DBs, logs must be ignored — the security review's secrets findings make
  the .gitignore part of this task).
