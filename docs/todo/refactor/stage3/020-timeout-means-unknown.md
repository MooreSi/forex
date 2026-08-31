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

---

## The fix did not reach the primary path — found 2026-08-31

Driving this task's killer demo end-to-end offline
(`tests/e2e/test_killer_demos.py::test_020_*`) showed the signal coming to rest
in **`pending`**, not `unknown`. Three separate defects, each of which alone
was enough to undo the whole task, and **every unit test passed throughout**
because none of them ran the caller.

### 1. The routing was never wired into the Telegram path

`_route_failed_open` lives in `open_from_signal.py` and runs in
`open_trade_from_signal`'s `except`. But the fresh-Telegram-signal route does
not call `open_trade_from_signal` at all — `scan_auto_execute` calls
`core_open_trade.open_trade` directly, and its own handler called
`reset_signal_to_pending(signal_id)` on **every** exception, `SendOutcomeUnknown`
included.

That is the primary path. The task shipped covering the internal-engine and
queued-fill routes only.

`scan_auto_execute.py` had already been bitten by exactly this shape once — its
own comment records the trading-schedule gate being missed on this path
"while queued zone-fills, pending-order fills, IME trades and the internal
engines were all correctly blocked".

**Fixed:** the handler now branches on `send_outcome_is_unknown(e)` and parks
instead of resetting.

### 2. `park_signal_unknown` could not park from this path's state

Its guard was `status='activating'` — the status `open_trade_from_signal`
leaves a signal in. On the Telegram path the signal is **`active`**. So even
once the routing was wired, the UPDATE matched no row: the park logged
success and changed nothing, leaving the signal re-claimable, since
`claim_signal_activation` accepts `status IN ('pending','active')`.

**Fixed:** guarded on both in-flight statuses. `closed`, `cancelled`,
`pending` and `failed` still cannot be parked, with a test each.

### 3. `reset_signal_to_pending` was the unguarded second door

There are two functions that hand a signal back to the scheduler.
`restore_signal_after_failed_open` was guarded (and tested — the guard was
found untested by mutation while 020 was being written).
`reset_signal_to_pending` was not, and it is the one this path calls. Even with
1 and 2 fixed, the generic handler on the way out would overwrite the park.

**Fixed:** `AND status != 'unknown'`.

### Verification

Eleven mutations across the five demos, all killed. For this task specifically:
un-wiring the routing, narrowing the park guard back to `activating`, and
dropping the `!= 'unknown'` clause each produce a red test.

Mutation 2 is the one worth remembering: the routing fires, the log says
`parking signal ... NOT retrying`, and the database is unchanged. A silent
no-op that reports success is the failure mode this repo's rules exist for.

**Still not `done`** — the demo needs a terminal. See
[docs/simon-handover/013-the-five-demos-runbook.md](../../../simon-handover/013-the-five-demos-runbook.md).

---

## A third route, found 2026-08-31: the answer lost between app and bridge

020 was implemented **inside** `mt5_bridge`: `order_send` returning `None` is
flagged `unknown: True`. That covers an answer lost inside the bridge process.
It does not cover an answer lost between the app and the bridge.

`MT5BridgeClient.place_order` wrapped its HTTP call in
`except Exception: return {"error": str(e)}`. So a **read timeout** — which
happens after the request reached the bridge, and after the bridge may already
have called `order_send` — arrived at `open_trade` looking exactly like a
broker rejection:

```python
_raise_if_send_unknown(mt5_result)      # only fires on unknown=True
if mt5_result.get("error"):
    raise RuntimeError(f"MT5 order rejected: ...")
```

A `RuntimeError` is not a `SendOutcomeUnknown`, so the signal was restored to
`pending` and sent again — for an order that may already be on the book.

**The dedup gate does not cover this.** `_resolve_fallback_send` only consults
the broker when the EA was actually asked (`ea_attempted`). On a
Python-bridge-only install there is no EA, so nothing checks.

### The distinction that matters

Not every transport failure is unknown, and treating them alike would be its
own bug:

| httpx exception | Meaning | Verdict |
|---|---|---|
| `ConnectError`, `ConnectTimeout`, `PoolTimeout` | nothing left this machine | retryable — and marking these unknown would park a signal every time the bridge restarts |
| `ReadTimeout`, `ReadError`, `WriteTimeout`, `WriteError`, `RemoteProtocolError` | request was on the wire; reply lost | **unknown** |

Anything not recognisably never-sent is treated as unknown — the conservative
direction, since a wrongly-parked signal waits for reconciliation while a
wrongly-retried one can become two live orders.

### Two fixes

1. `mt5_client._send_failure` classifies the exception, on all four send paths
   (`place_order`, `close_position`, `partial_close`, `modify_order`). A lost
   answer on a **close** matters for the same reason: recording it as closed
   books a P&L that may not have happened.
2. `send_outcome_is_unknown` now knows about httpx. `httpx.ReadTimeout` is not
   a builtin `TimeoutError` and inherits from none of the types that tuple
   listed, so one escaping the client was read as a rejection. The client
   returns a dict rather than raising, so this is a backstop — but the
   classification lived in one place and that place did not know about the
   transport library actually in use.

16 client tests, 8 classifier tests, one end-to-end through the real client.
Five mutants, all killed, including both over-parking and under-parking.

### Still open

`mt5_native.py` (the in-process bridge, used when `mt5_native_bridge_enabled`)
has the same `except Exception: return {"error": str(e)}` shape on its four
send paths. It has **not** been changed: its failures come from a thread
executor rather than a socket, and I cannot reason about which of them mean
"the call never ran" without being able to exercise it. Deliberately left
rather than guessed at — see `docs/simon-handover/016`.

**Still not `done`** — the demo needs a terminal.
