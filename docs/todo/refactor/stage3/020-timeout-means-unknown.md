# 020 — Timeout means UNKNOWN: never retry, never re-pend a possibly-filled order

**Status:** **code + tests DONE 2026-08-29 (market closed). NOT Done** — the killer
demo (fake a lost response after a fill) needs a live broker.
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

---

## Built 2026-08-29 (market closed, no demo yet)

### The bridge half

`mt5_bridge._place_order` walks three filling modes. On `order_send` returning
`None` it **continued to the next mode and sent again**. `None` is "the
response was lost", not "nothing filled" — so if the first send did fill, the
retry opens a second position. It now `break`s and reports `unknown: True`.

The filling-mode retry itself is untouched and there is a test saying so: a
retcode of 10030 is the broker explicitly stating the mode is wrong and nothing
filled, which is real information and worth retrying. Only `None` stops.

### The signal half

New signal status **`unknown`**. `status` is TEXT with no constraint, so no
migration was needed.

`signal_state_repo.park_signal_unknown(signal_id, reason)` moves an
`activating` signal to `unknown` and appends the reason to `notes` (appends,
because 030's reconciler needs the reason and whatever was already recorded is
not ours to discard).

`open_from_signal` used to call `restore_signal_after_failed_open` on **any**
exception. It now routes:

| Failure | Result | Why |
|---|---|---|
| Broker rejection, guard rejection (`ValueError`) | `pending`, retryable | Nothing filled; a retcode saying no is information |
| Timeout, `ConnectionError`, `OSError`, `SendOutcomeUnknown` | `unknown`, parked | The order may be on the book |

The scheduler needed no change — it selects `status='pending'` — but there is
now a test asserting an `unknown` signal is not returned, because that is the
property the parking depends on.

### It also closed 010's deferred case

010 shipped with dedup-UNKNOWN still sending, because there was nowhere safe to
put a signal that could not be resolved. With the park available it now raises
`SendOutcomeUnknown` and stops. That test previously asserted the opposite and
said in its own docstring that it should change when 020 landed; it now asserts
the parking.

### Found while checking my own work

`restore_signal_after_failed_open` has always been guarded on
`status='activating'`, and **that guard had no test** — dropping it passed
everything. Three tests added: it restores an activating signal, does not
resurrect a closed one, and does not resurrect an `unknown` one. The last is
the interaction that matters now, since a stray restore would undo the parking.

### Not done

The **killer demo**: fake a lost response after a fill, confirm the signal
parks and the scheduler never touches it again. Needs a live broker.

Until [030](030-broker-db-reconciliation.md) ships, a parked `unknown` signal
stays parked and its possible fill is unmanaged. That is strictly safer than
today's double-fire, and it is why 030 follows immediately.
