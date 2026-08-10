# 040 — record_close idempotency guard

**Status:** not started
**Depends on:** phase 1 landed (1/040 reduced the caller set to the guarded wrappers)
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
The frozen path itself is edited here — this is the pack's most sensitive task.
**Layer:** service
**Leverage:** 1/040 already routed monitor_loop through the runtime wrappers, so the caller graph
is now small and known

## Problem

`record_close` has no status/idempotency guard — its own comment admits it (review risk H5). Five
callers (monitor loop, reconciliation, manual close, partial-close completion, sync) can race, and
a double call double-counts P&L, double-feeds the breaker, and corrupts the books.

## Decision

Add a compare-and-set status transition at the top of the close-recording transaction: only an
`open` trade may transition to `closed`; a second caller finds `closed` and returns a no-op result
(logged at info with both call sites). This is a **guard prepended inside the frozen function's
transaction** — the recording logic itself is not reshaped. Per the golden rules, freezing means
"never reshaped without owner sign-off and a demo session" — this task exists to obtain exactly
that sign-off, and the diff must be reviewable as guard-only.

## What must NOT change

- Everything below the guard in `record_close` — byte-identical (diff-reviewed line by line).
- `close_trade`, `_make_close_trade_ctx`, `partial_close_trade` — zero edits.
- All existing close-path witness tests pass unmodified.
- The close *outcome* for every single-caller scenario — characterization-pinned before the change.

## Tests first (TDD)

- `tests/trading/test_record_close_idempotent.py::test_second_record_close_is_noop` — two calls,
  one P&L row, one breaker feed — regression
- `::test_concurrent_record_close_single_winner` — two threads, event-synchronised, one wins — behaviour
- `::test_noop_result_is_distinguishable` — callers can tell no-op from success (reconciliation
  needs this) — surface
- `::test_partial_close_unaffected` — partial closes don't trip the full-close guard — boundary
- Characterization capture: `::test_single_close_outcome_unchanged` — full recorded row identical
  to a pre-change capture — characterization + negative control (perturb the fake, capture differs)

## What to do

1. `/safe-change` protocol first; owner sign-off on the guard design **before** code.
2. Write the tests above; run them; confirm they fail for the right reason (the double-count must
   reproduce against today's code).
3. Add the compare-and-set guard inside the existing transaction; nothing else moves.
4. Audit all five call sites for retry loops that assumed non-idempotency; simplify only with
   evidence.
5. `python -m tools.checks all`.

## Where

- the frozen close-recording function (located via `runtime.py:420-506` wrappers) — guard only
- call sites — audit, minimal touch

## Acceptance

- Double-call and concurrent-call tests green; single-call characterization byte-identical.
- **The killer test (demo session):** close a demo position while forcing the monitor loop and a
  manual close to collide; books show exactly one close.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- If the diff cannot be kept guard-only, stop and bring the actual diff to the owner — that is the
  golden-rule tripwire working as intended.
