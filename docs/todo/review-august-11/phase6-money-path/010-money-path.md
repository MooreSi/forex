# 010 — Money-path for Simon (drives review-august-08 phase 1)

**Status:** blocked — Simon sign-off + demo session · **Touches money:** YES (all of it)
**Drives:** [../../review-august-08/phase1-stop-the-bleeding/](../../review-august-08/phase1-stop-the-bleeding/README.md) — do NOT duplicate; this is the index + sequencing.

## Problem

The live-safety fixes are specced and test-planned but unshipped: one signal can still fire two live
orders; broker and DB can disagree with no reconciliation; a failed broker close can be recorded as
done; protective halts default off. These are the reasons the app is not yet safe to run live.

## The tasks (each detailed in review-august-08 phase 1; run in this order)

1. `010 order-send dedup` — trade id at the broker + pre-send check (SPEC-002 C1).
2. `020 timeout→UNKNOWN` — timeout/None/exception on send is UNKNOWN, never retried/re-pended.
3. `030 broker↔DB reconciliation` — startup + periodic; broker is the source of truth for existence.
4. `040 no DB close on a failed broker close` — monitor_loop routes through the frozen wrappers.
5. `060 protective halts on by default` — daily-loss / drawdown / circuit-breaker armed; un-swallow
   the breaker recording.

## What to do

1. **Simon at a demo terminal.** Each task runs through `/safe-change`. Confirm the review-august-08
   QUESTIONS money defaults (Simon) first.
2. Implement per each task's TDD contract (tests against fakes; no real/demo order in any test).
3. Each task's killer demo on Simon's machine; record sign-off + demo in review-august-08 PROGRESS.
4. `python -m tools.checks all` green throughout; the frozen close path untouched.

## Acceptance
- All five tasks Done with Simon sign-off + demo; the killer scenarios pass on his terminal
  (forced ack-timeout → one position; kill-between-place-and-record → adopted once; forced
  close-reject → DB stays open + alert). This is the gate for "safe to run live."
