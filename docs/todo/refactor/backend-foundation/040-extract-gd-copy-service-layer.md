# 040 — Extract gd_copy_signal's service layer

**Status:** not started
**Depends on:** 030-migrate-gd-copy-repo-layer.md
**Real-money surface:** no (still no MT5 connection — that's 050)
**Leverage:** `gd_copy_signal_repo.py` (030), `backend-conventions` §7 decomposition pattern,
020's characterization suite

## Problem

`gd_copy_signal/engine.py` is 1,295 lines mixing signal-generation triggering, TP/SL/
partial-close management, and VIP-correlation tracking in one file — above the 800-LOC ceiling
and mixing concerns `backend-conventions`' decomposition pattern (§7) says should split.

## Decision

Split `engine.py` into a thin `gd_copy_signal_service.py` (public orchestration surface) plus
sub-flow files, following the extraction order `backend-conventions` recommends: pure
functions first (already mostly isolated in `ict_patterns.py`/`level_detector.py`/
`signal_generator.py` — no change needed there), then completion/tracking handlers
(`gd_copy_signal_correlate.py` for VIP correlation), then transaction-wrapped writes last
(`gd_copy_signal_manage.py` for TP/SL/partial-close, calling into 030's repo transactions).
Each new file targets under 400 lines.

## Tests first (TDD)

- 020's engine characterization suite, re-pointed at `gd_copy_signal_service.py`'s public
  surface — must pass with zero modifications to its assertions.
- `tests/gd_copy_signal/test_service_surface.py` — a surface test asserting every function
  020's suite exercises is still exported from `gd_copy_signal_service.py`'s public namespace
  (catches a dropped or mis-wired re-export — per `backend-conventions` §7's guidance on
  decomposition-safe testing).

## What to do

1. Confirm 020's engine suite is green against current `engine.py` and 030's repo suite is
   green (prerequisites).
2. Extract `gd_copy_signal_manage.py` (TP/SL/partial-close orchestration) — calls
   `gd_copy_signal_repo.py`'s transaction-wrapped functions from 030.
3. Extract `gd_copy_signal_correlate.py` (VIP signal correlation tracking).
4. Reduce `engine.py` to `gd_copy_signal_service.py` — a thin orchestrator wiring generation
   (existing `signal_generator.py`) → management → correlation.
5. Re-run 020's full suite against the new module structure — must pass unchanged.
6. Add and pass `test_service_surface.py`.
7. Once green, remove the old `engine.py`/`database.py` in favor of the new modules — this is
   the cutover point within `forex-refactor2` (does not touch the live app).

## Where

- `forex_trader/gd_copy_signal/gd_copy_signal_service.py` (new, replaces `engine.py`)
- `forex_trader/gd_copy_signal/gd_copy_signal_manage.py` (new)
- `forex_trader/gd_copy_signal/gd_copy_signal_correlate.py` (new)
- `forex_trader/gd_copy_signal/engine.py` (removed once the above is green)
- `forex_trader/gd_copy_signal/database.py` (removed once 030+040 are green)
- `tests/gd_copy_signal/test_service_surface.py` (new)

## Acceptance

- 020's full characterization suite passes against the new file structure with zero
  modifications to the test assertions.
- No file in `gd_copy_signal/` exceeds 800 lines (target well under).
- `test_service_surface.py` passes.
- **The killer test:** 020's full-lifecycle test (create → trigger → partial → close, balance
  check) still passes end-to-end through the new service+repo stack.

## Notes

This is the task that proves whether the 010/030 pattern actually works cleanly on a real
engine. If it doesn't fit well, that's real signal to bring back to Simon before applying the
same pattern to a bigger engine later.
