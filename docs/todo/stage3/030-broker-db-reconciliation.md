# 030 — Broker↔DB reconciliation service

**Status:** not started
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
