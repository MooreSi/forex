# 040 — Docs phase: write down what shipped

**Status:** not started
**Depends on:** everything user-visible in phases 1–4 that actually shipped
**Touches money:** no
**Layer:** docs
**Leverage:** CHANGELOG.md exists; docs/system/rules/ rules exist; the pack's SUMMARY.md is the raw material

## Problem

This pack changes things users and future sessions must know about: protective halts switch on by
default (with the thresholds the owner chose), send-timeouts now park signals in a visible UNKNOWN
state, the dashboard binds to localhost, auto-update is off pending signing, first boot after
upgrade runs migrations (and takes longer), backups appear in a folder, and several docs/ai rules
gained enforcement (cycle gate, fail-closed gates). Unwritten, each becomes a support question or
a bad assumption.

## Decision

One docs task at the end rather than per-task doc edits, so the user-facing story is written once,
coherently, against what *actually* shipped — cross-checked against PROGRESS.md, not against the
plans.

## What must NOT change

- `docs/todo/refactor/stage0/` — untouched, as ever.
- No doc may claim anything PROGRESS.md can't back with a Done row + verification paste.

## Tests first (TDD)

- N/A — docs only. The review discipline instead: every claim in the CHANGELOG entry is traced to
  a PROGRESS.md row in the PR description.

## What to do

1. CHANGELOG.md entry for the release that carries this pack: halts-on-by-default (numbers),
   UNKNOWN state, localhost bind, update-channel default, migration-on-first-boot note, backups.
2. In-app setup/about text: localhost + no-login wording (phase1/050 touched it; finalize),
   update panel disabled-state text (phase2/070).
3. docs/ai updates: 30-architecture.md gains the no-cycle rule; 40-testing.md gains the
   fail-closed gate doctrine + the canonical `fresh_db`; 20-trading-safety.md gains UNKNOWN-state
   semantics and the reconciliation contract.
4. Update the two anchor specs' Verification checklists to Shipped.
5. `python -m tools.checks all` (docs shouldn't break it; prove it anyway).

## Where

- `CHANGELOG.md`, `frontend/app.py` setup text, `docs/system/rules/*.md`, `docs/specs/002/003`

## Acceptance

- A user reading CHANGELOG + setup text learns every behaviour change without reading this pack;
  every claim traces to a Done row.
- This is the last task before `/spec done` retires the pack.
