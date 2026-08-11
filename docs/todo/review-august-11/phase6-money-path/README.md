# Phase 6 — Money-path (safe with real money — Simon's demo)

**Status:** blocked — Simon's sign-off + a demo session
**Gated on:** Simon
**Touches money:** YES — every task here.

## Goal of this phase

The app is safe to run with real money: one signal can only ever fire one live order; the DB never
disagrees with the broker without reconciliation; a failed broker close is never recorded as done;
and the protective halts are on by default. This **drives review-august-08 phase 1** (already specced
and test-planned under anchor specs SPEC-002/003) rather than duplicating it. Nothing here ships
without Simon at a demo terminal.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-money-path.md](010-money-path.md) | Index + sequencing of the review-august-08 phase-1 money tasks (dedup, timeout→unknown, reconciliation, no-db-close-on-failed-close, halts-on) | YES |

## Drives / references

[../../review-august-08/phase1-stop-the-bleeding/](../../review-august-08/phase1-stop-the-bleeding/README.md)
and anchor specs — note: the anchor specs (SPEC-002/003) were lost in a docs reorg; their substance
survives in that pack's phase-1 task files. Re-materialise the anchors if Simon wants the formal
Problem/Non-goals/Test-plan documents.

## Exit criteria

- Each task's killer demo passes on Simon's demo terminal (forced ack-timeout → one position;
  kill-between-place-and-record → adopted once; forced close-reject → DB stays open + alert).
- All money tasks Done with Simon sign-off + demo recorded in review-august-08 PROGRESS.
- `python -m tools.checks all` green; the frozen close path untouched throughout.
