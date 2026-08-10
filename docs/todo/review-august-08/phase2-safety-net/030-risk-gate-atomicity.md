# 030 — Risk gates: reserve before await, no check-then-act race

**Status:** not started
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
