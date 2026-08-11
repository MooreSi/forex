# 030 — Frontend hygiene: silent excepts, blocking timers, upgrade canary

**Status:** not started · **Touches money:** no · **Layer:** frontend
**References:** [../../review-august-08/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md](../../review-august-08/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md).

## Problem

44 `except Exception: pass` in UI paths (regressed from 31) silently drop data — incl. history.py
dropping malformed deals from displayed P&L. 33 hand-rolled `ui.timer` polls run synchronously on the
event loop. `app.py:15-59` monkey-patches NiceGUI internals — and the installed NiceGUI is now 3.15.0
while the patch targets 3.12.1, with no canary (an upgrade breaks the app silently).

## Tests first (TDD)
- `tests/frontend/test_no_silent_excepts.py::test_no_bare_except_pass_under_frontend` — AST, shrinking
  baseline to 0 (+ negative control: planted swallow fails) — structural
- `tests/frontend/test_nicegui_canary.py::test_patched_internals_exist` — every attribute app.py
  patches exists on the installed NiceGUI (fails on the next incompatible upgrade) — structural canary
- `tests/frontend/test_poll_helper.py::test_fetch_runs_off_event_loop` — the shared poll helper offloads — behaviour

## What to do
1. Write the tests (calibrate the AST count at 44); build a shared `components/poll.py` helper.
2. Replace each swallow with log-at-warning + a visible "data incomplete" marker; migrate the 33
   timers to the poll helper; add the NiceGUI canary.
3. `python -m tools.checks all`.

## Where
- `frontend/pages/*`, `frontend/components/poll.py` (new), `frontend/app.py` (canary target).

## Acceptance
- Silent-except AST count at 0 (shrinking baseline); timers offloaded; canary red on an incompatible
  NiceGUI. Green suite.
