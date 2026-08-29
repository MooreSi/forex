# 030 — Broker↔DB reconciliation service

**Status:** **HALF built 2026-08-29 (market closed).** The diff engine and the
report-only pass are in and wired. **The repairers are NOT built.** Not Done.
**Depends on:** 020-timeout-means-unknown.md
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
**Layer:** service
**Leverage:** frozen-path wrappers `backend/src/runtime.py:420-506` (close recording routes through
these); existing broker position/deal queries; miss-streak=2 confirmation logic stays as-is

## Problem

Broker and DB are dual-written with no arbiter (review data C1): `open_trade.py:334-354` places the
real order then inserts the DB row — a crash between leaves a live position the app doesn't manage.
The mirror gap exists on close. Nothing anywhere scans MT5-vs-DB for orphans, and 020's UNKNOWN
signals need a resolver.

## Decision

New `services/positions/reconciliation.py` per SPEC-003: at startup (before the monitor loop starts
managing) and every N seconds, join broker positions + recent deals against DB open trades on
ticket + trade id; emit a typed diff; repair DB-side only. Broker-side is **never** touched —
reconciliation is read-only at the broker. First release runs report-only by default (QUESTIONS.md
#2). Chosen over wrapping open/close in try/finally compensation because a crash kills any
in-process compensation; only an independent, restart-surviving pass closes the gap.

## What must NOT change

- Reconciliation must be provably broker-read-only: it never imports or calls order send/modify/
  close. (Structural test below.)
- The frozen close path is *called* (via the runtime wrappers) for `db_only` repairs — no third
  close-recording variant. The existing near-copies in monitor_loop are task 040's problem, not
  license to add another.
- miss-streak=2 close confirmation — byte-identical.
- Existing close-path witness tests pass unmodified.

## Tests first (TDD)

- `tests/positions/test_reconciliation.py::test_broker_only_position_adopted_as_recovered` —
  fake broker holds a position absent from DB → `recovered` row inserted, loudly logged — behaviour
- `::test_db_only_trade_closed_from_broker_deal_history` — DB-open trade absent at broker, closing
  deal in history → close recorded through the runtime wrapper with broker numbers — behaviour
- `::test_db_only_without_deal_evidence_is_flagged_not_closed` — no deal found → flagged for the
  owner, DB left open — boundary
- `::test_unknown_signal_resolved_to_open` / `::test_unknown_signal_resolved_to_failed` — 020's
  UNKNOWN resolves both directions from broker truth — behaviour
- `::test_matched_positions_are_untouched` + negative control (mutate the fake to mismatch and
  assert the detector fires) — control
- `::test_report_only_mode_repairs_nothing` — diffs reported, zero writes — behaviour
- `::test_reconciliation_never_calls_order_functions` — structural: module import graph contains no
  send/modify/close symbol — structural

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Build the diff engine (pure function: broker snapshot + DB snapshot → typed diff) — this is the
   testable core; keep it free of I/O.
3. Add the repairers behind the report-only flag; route `db_only` closes through
   `runtime.py:420-506` wrappers.
4. Wire startup ordering: reconcile once **before** the monitor loop begins managing; then a
   periodic task (interval via `/add-tunable`, start 60s).
5. Telegram/log notification on every repair or flag.
6. `python -m tools.checks all`.

## Where

- `backend/src/services/positions/reconciliation.py` — new module (keep under 800 lines; split diff
  engine vs repairers if it grows)
- `backend/src/runtime.py` — startup ordering + task registration only
- `backend/src/services/positions/` repo — the `recovered` state

## Acceptance

- Kill-between-place-and-record (simulated with fakes) is repaired on next start: adopted exactly
  once, idempotent on the run after.
- **The killer test (demo session):** place a demo position via the app, kill the app before the DB
  insert (breakpoint/kill switch), restart → position adopted exactly once as `recovered`.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- QUESTIONS.md #2 (report-only week + interval) and #6 (no-id manual positions) gate the repairer
  defaults. The existing auto-adopt importer (risk H6) is *superseded or subordinated* here per the
  #6 answer — don't leave two adopters running.
- Deals-history lookback shared with 010's dedup window — one tunable, not two.

---

## Built 2026-08-29: the arbiter, reporting only

Simon's answer in [001-trading-defaults](../../../simon-handover/001-trading-defaults.md)
is *"report-only for the first week, then switch to repair"*. That first week
is what this delivers, and nothing more.

### The diff engine

`services/positions/reconciliation.py::diff_snapshots` — broker positions +
broker deals + DB open trades + parked `unknown` signals in, typed differences
out. **A pure function with no I/O**, which is the point: it is the part where
a mistake is expensive and a test is cheap.

| Kind | Meaning |
|---|---|
| `matched` | open at the broker and in the database |
| `broker_only` | live at the broker, unknown to the DB — **nothing is managing it** |
| `db_only_closed` | gone from the broker, and a closing deal explains it |
| `db_only_no_evidence` | gone, and nothing explains it — flagged, never closed |
| `unknown_filled` / `unknown_not_filled` | 020's parked signals, resolved from broker truth |

Matching is by ticket, falling back to the order comment for a row that has no
ticket yet (an EA template placeholder). The comment vocabulary is shared with
`broker/dedup.py` so one trade is recognised the same way wherever it is looked
for, and the deal-history window is the same one constant, per the spec's "one
tunable, not two".

`db_only_no_evidence` is the boundary that matters: no position and no deal is
**not** proof a trade closed. It is equally consistent with a broker read that
failed, and booking a close on that basis would fabricate an outcome.

### Read-only at the broker, structurally

An arbiter that can place or close orders is just another writer.
`diff_snapshots` is never handed a bridge — a test asserts the signature
contains no such parameter — and a second test parses the module's **AST** and
fails if it calls `place_order`, `close_position`, `modify_order`,
`order_send`, `open_trade`, `partial_close_trade`, `record_close` or
`close_trade`.

The AST matters. The first version of that test scanned the source text and
failed on the docstring, which *explains why* those must not appear — it would
have failed on an accurate comment and passed on an obfuscated call.

### Wired, not shelved

`collect_and_report` runs from the monitor cycle every 12 cycles. It reads both
sides and logs what disagrees; it writes nothing, so it needed no
startup-ordering change — *"reconcile before the monitor loop manages"* is
load-bearing for **repair**, not for a report that cannot change anything.

It was tempting to allowlist the module as an orphan and wire it later. That is
exactly the failure this repo's CLAUDE.md opens with — thousands of lines of
extracted code nothing called — so it is wired.

A failed read on either side reports **nothing** rather than diffing half a
picture: an empty broker read would otherwise look like every trade having
vanished, and the report would be a page of false alarms. It also never raises
into the monitor loop, because losing position management is far worse than
losing a report.

### Deliberately not done

- **The repairers.** No `recovered` insert, no close-from-deal, no releasing a
  parked signal. Those write, and they route through the frozen close path, so
  they want their own change and a demo.
- **The interval tunable.** The spec asks for one; it should land with the
  repairers, when the cadence starts to mean something. A dial that only
  changes how often a log line appears is not one a trader wants to move
  ([60-adding-a-tunable](../../system/rules/60-adding-a-tunable.md): "expose a
  constant when a TRADER would want to move it").
- **The killer demo:** kill the app between place and DB-record, restart,
  confirm the position is adopted exactly once. Needs a live broker.
