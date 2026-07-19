# 040 — Extract gd_copy_signal's service layer

**Status:** Done (2026-07-19) — with a scope correction, see Notes
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
7. ~~Once green, remove the old `engine.py`/`database.py`~~ — **did not do this, see Notes.**

## Where

- `forex_trader/gd_copy_signal/gd_copy_signal_service.py` (new, replaces `engine.py`'s role)
- `forex_trader/gd_copy_signal/gd_copy_signal_manage.py` (new)
- `forex_trader/gd_copy_signal/gd_copy_signal_correlate.py` (new)
- `forex_trader/gd_copy_signal/gd_copy_signal_live_execute.py` (new — split out separately from
  the original plan, see Notes)
- `forex_trader/gd_copy_signal/engine.py` (left in place, still imported elsewhere — see Notes)
- `forex_trader/gd_copy_signal/database.py` (left in place, still imported elsewhere — see Notes)
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
engine. It does — 4 files, all well under budget (`gd_copy_signal_service.py` 624 lines,
`gd_copy_signal_repo.py` 677, `gd_copy_signal_manage.py` 313, `gd_copy_signal_correlate.py`
273, `gd_copy_signal_live_execute.py` 174), 116 tests all green, extraction done by literal
code relocation (mixins composed into `GDCopyEngine`) rather than a rewrite, so behavior risk
stayed low.

**Split into 4 files, not 3** — `_try_live_execute` (the real-order dispatch path) got its own
`gd_copy_signal_live_execute.py` rather than living in the service file, since
`backend-conventions` §7 calls out "the writes: dispatch/submit" as its own extraction target,
and it's the one method with an actual real-money surface — worth isolating for that reason
alone.

**Fixed one more raw-SQL-outside-the-repo violation while extracting**: `_run_cycle`'s
consecutive-loss cooldown check used a raw `gdc_db._conn()` query inline (engine.py:319-325,
flagged in 020's scope note). `gd_copy_signal_repo.py` doesn't expose `_conn()` at all, so this
had to become a proper named function (`get_recent_outcomes_by_direction`) rather than a
workaround — a forced, low-risk fix rather than optional scope creep.

**Scope correction — did NOT delete `engine.py`/`database.py` (2026-07-19):** the original task
plan assumed a clean cutover once tests were green. Before deleting, `grep` turned up 7 files
outside `gd_copy_signal/`'s core modules still importing the old `engine`/`database` names:
`ui/app.py`, `ui/pages/gd_copy_panel.py`, `ui/pages/remote_node.py`, `core/app_lifecycle.py`,
`sync/server.py`, plus `gd_copy_signal/ml_engine.py` and `telegram_research.py`. Deleting the
old files now would have broken the app's actual startup/UI/sync wiring — directly against
"no UI changes" and "don't break anything." **The new modules exist in parallel, fully tested,
but nothing in the running app uses them yet.** Wiring those 7 call sites over to
`gd_copy_signal_service.py`/`gd_copy_signal_repo.py` (and then deleting the old files) is real,
separate follow-up work — effectively a "task 045" this pack didn't originally account for.
Flagged in PROGRESS.md; worth deciding explicitly with Simon before 050, since 050's demo
validation should probably run against whichever code path the live app will actually use.
