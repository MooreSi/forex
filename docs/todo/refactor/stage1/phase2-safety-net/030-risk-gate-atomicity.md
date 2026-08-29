# 030 — Risk gates: reserve before await, no check-then-act race

**Status:** **not started — but the design changed, see the note at the bottom
(2026-08-29).** A prerequisite landed; the gate itself is still racy.
**Depends on:** phase 1 landed (gates armed by 1/060; send path stabilised by 1/010–020)
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
**Layer:** service
**Leverage:** the atomic signal claim already in the codebase is the pattern to copy — claim first,
act second, release on failure

## Problem

`max_open_trades` and the circuit-breaker checks are check-then-act across broker awaits
(`open_trade.py:203-206`, review data H5): two concurrent signals can both observe "0 open, under
the cap", both pass, and both place real orders. The only always-on protection the system has can
be raced past.

## Decision

Reserve a trade slot **before** any await: an atomic counter/claim (single SQLite transaction,
mirroring the signal-claim pattern) that increments inside the gate check; release on definitive
failure; keep on fill or UNKNOWN (an UNKNOWN might be filled — the slot stays taken until
reconciliation resolves it). All risk gates (cap, breaker, halts) evaluate inside the same claim
transaction.

## What must NOT change

- Gate *thresholds and semantics* — byte-identical to what phase 1/060 locked. This task changes
  only *when* they are evaluated (atomically) not *what* they allow.
- The frozen close path; slot release on close hooks the existing close recording, it does not
  modify it.
- Single-signal behaviour: one signal through an idle system behaves exactly as before.

## Tests first (TDD)

- `tests/risk/test_slot_reservation.py::test_concurrent_signals_cannot_both_pass_cap` — two
  concurrent open attempts against cap=1 with a slow fake broker → exactly one proceeds — behaviour
  (the race, made deterministic with an event-controlled fake)
- `::test_slot_released_on_definitive_failure` — broker rejects → slot free again — behaviour
- `::test_slot_held_on_unknown` — timeout/UNKNOWN → slot stays taken — boundary
- `::test_slot_released_on_close` — close recording frees the slot — wiring
- `::test_single_signal_path_unchanged` — negative control: idle system, one signal, identical
  outcome to a characterization capture from before the change — control
- `::test_restart_rebuilds_slots_from_open_trades` — slots derive from DB truth on boot, no leak — boundary

## What to do

1. Write the tests above; run them; confirm they fail for the right reason (the race test must
   demonstrably double-pass against today's code first).
2. Build the slot claim in the trading service (same transaction discipline as the signal claim).
3. Move the gate evaluations of `open_trade.py:203-206` inside the claim; thread release into the
   failure and close paths.
4. Reconciliation (1/030) resolves UNKNOWN → resolve the slot with it.
5. `python -m tools.checks all`.

## Where

- `backend/src/services/trading/open_trade.py` — gate relocation
- `backend/src/services/risk/` — the claim primitive
- trade repo — slot state derivation

## Acceptance

- The deterministic race test: cap=1, two signals, slow broker → exactly one order, forever.
- **The killer test (demo session):** fire two demo signals as close to simultaneously as the app
  allows with cap=1 → one demo position.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- This is the task where the two writer threads meet the DB — coordinate with 050's write lock;
  land whichever first, but the claim must be correct under both.

---

## Design note, 2026-08-29 — a simpler fix than a new counter, and why it waits

### The race is confirmed still present

`open_trade` reads `count_open_trades()`, compares it to the cap, then does
several awaits (tick fetch, EA handoff, `place_order`) before the INSERT. Two
concurrent signals both see "under the cap" and both place.

### The obvious fix does not work

"Also count signals in `activating`" is wrong, and symmetrically so. With
`max_open_trades=1` and two signals claiming at once, each sees one *other*
claim in flight and **both** refuse. Counting cannot break a tie between equals.

### What does work

Move the cap check **into** the claim, so the test and the write are one
statement. SQLite serialises writers, so the second claim sees the first:

```sql
UPDATE vantage_signals SET status='activating', activated_at=?
WHERE signal_id=? AND status IN ('pending','active')
  AND (SELECT COUNT(*) FROM vantage_simulated_trades WHERE status='open')
    + (SELECT COUNT(*) FROM vantage_signals WHERE status='activating')
    < :max_open_trades
```

First claim: `0 + 0 < 1`, claims. Second: `0 + 1 < 1` is false, refuses. No
window, and it reuses the atomic claim that already exists rather than adding a
reservation table.

Keep the existing check in `open_trade` as well — it is the backstop for the
paths that never claim a signal at all (manual market orders, IME).

### Why it is not done tonight

**The failure mode is worse than the bug.** A claim that leaks consumes a slot
permanently, and once the cap fills nothing trades at all — silently. That is
bugs/016 in a different table, and it is a far worse outcome than the
occasional double-open this fixes.

That risk is only acceptable with a release valve, which is why the sweep below
came first.

### Prerequisite: DONE (2026-08-29)

`signal_state_repo.release_stranded_activations()` now puts abandoned
`activating` claims back to `pending` after 15 minutes, and
`claim_signal_activation` stamps `activated_at` with the claim time so the
sweep can tell abandoned from in-flight. It runs from the reconciliation pass.

That was a live bug on its own: **a crash between the claim and any exit path
stranded the signal forever.** The scheduler only selects `pending`, so the
signal was not failed, not queued and not visible anywhere — it was simply
gone, and nothing swept for it.

### Remaining work

The single-statement claim above, plus its tests, plus a demo. One focused
session — it should not be bolted onto the end of a long one, on the one gate
that can stop all trading.
