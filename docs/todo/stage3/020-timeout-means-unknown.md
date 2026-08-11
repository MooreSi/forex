# 020 — Timeout means UNKNOWN: never retry, never re-pend a possibly-filled order

**Status:** not started
**Depends on:** 010-order-send-dedup.md
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
**Layer:** service
**Leverage:** SPEC-002 design; the signal state machine already has an atomic claim to extend

## Problem

Two paths treat "no response" as "not filled" (review risk C2/C3):

- `open_from_signal.py:95-98` — a 15s HTTP timeout on `order_send` is treated as a rejection; the
  signal is restored to pending and can re-open. If the order actually filled, that's a
  filled-but-unrecorded live position **plus** a second order on the retry.
- `mt5_bridge.py:711-728` — `_place_order` retries `order_send` after a `None` result. A `None` is
  "response lost", not "not filled"; the retry can double-fill.

## Decision

Introduce an `UNKNOWN` signal state. Any timeout / `None` / transport exception on send transitions
the signal to `UNKNOWN` — not failed, not pending, not retryable. Only reconciliation (task 030,
SPEC-003) may resolve `UNKNOWN`, from broker truth. The bridge retry-after-None is deleted outright.
Chosen over "retry with dedup check" because in phase 1 the safe primitive is *stop*; smart resends
can come later on top of 010's dedup.

## What must NOT change

- The atomic signal claim — byte-identical.
- Genuine broker *rejections* (an actual retcode saying no) keep their current handling — this task
  only reroutes the no-response cases.
- The frozen close path — untouched.
- Existing signal-lifecycle tests pass unmodified except any that pin the C2/C3 bugs themselves —
  if one exists it is evidence the bug was enshrined; flag it to the owner, do not silently rewrite.

## Tests first (TDD)

- `tests/trading/test_send_unknown_state.py::test_send_timeout_marks_signal_unknown` — fake
  transport raises timeout → signal state UNKNOWN, not pending — behaviour
- `::test_unknown_signal_cannot_reopen` — the open-from-signal scheduler skips UNKNOWN signals — boundary
- `::test_bridge_place_order_does_not_retry_on_none` — fake `order_send` returns None once, counts
  calls; exactly one call — regression
- `::test_explicit_rejection_still_fails_normally` — a real retcode rejection follows the existing
  failed path (negative control proving UNKNOWN is reserved for no-response) — control
- `::test_unknown_transition_is_persisted` — UNKNOWN survives restart (it must be visible to
  reconciliation) — wiring

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Add the `UNKNOWN` state to the signal state machine + persistence (repo column/state value —
   check the migration lands via the current ALTER mechanism until phase2/020 replaces it).
3. Reroute `open_from_signal.py:95-98`: timeout/transport-error → UNKNOWN (with the raw error
   recorded on the signal for the reconciler).
4. Delete the retry loop in `mt5_bridge.py:711-728`; `None` → report unknown upward.
5. Make the pending-signal scheduler explicitly skip UNKNOWN.
6. `python -m tools.checks all`.

## Where

- `backend/src/services/trading/open_from_signal.py` — timeout rerouting
- `mt5_bridge.py` — retry deletion
- signal state machine + its repo (locate via `services/signals/`) — new state

## Acceptance

- No code path re-sends or re-pends after a no-response send; grep shows zero retry loops around
  `order_send`.
- **The killer test:** fake a lost response after a fill; the signal parks in UNKNOWN and the
  scheduler provably never touches it again (until 030 resolves it).
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Until 030 ships, an UNKNOWN signal stays parked and its possible fill is unmanaged — that is
  still strictly safer than today (double-fire), but it is why 030 follows immediately.
- UI: UNKNOWN should be visible wherever signal states are shown; keep it a plain state-name
  passthrough (no new UI surface — no BAR.md needed).
