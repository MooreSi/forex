# 050 — Frontend: no silent excepts, no blocking timers, a canary on the monkey-patch

**Status:** not started
**Depends on:** 030 (land inside the restructured shapes, not the old monoliths)
**Touches money:** no (display-layer only; but silent display of wrong P&L is why it matters)
**Layer:** frontend
**Leverage:** `ai_trade_analysis.py` already offloads to an executor — the in-house pattern to
copy; `components/` (seeded by 030) is where the shared helpers live

## Problem

Review frontend #5/#6/#8: 31 `except Exception: pass` in UI refresh paths — `history.py:767-768`
silently drops malformed deals from the *displayed P&L*, so the window onto live trades can lie by
omission. 33 hand-rolled `ui.timer` polls, five on history.py alone, run synchronously on the
event loop. `app.py:15-59` monkey-patches NiceGUI 3.12.1 private internals with no
upgrade-canary — a version bump breaks the app in ways nothing detects.

## Decision

Replace every swallow with the house policy: log at warning with context + surface a visible
"data incomplete" marker in the affected widget — a UI that can't render a row says so. Convert
the timer polls to the executor-offload pattern via one shared `poll(interval, fetch, render)`
helper in `components/`. Add a canary test that pins the patched NiceGUI internals by name so an
upgrade fails the suite instead of the app.

## What must NOT change

- Displayed values for well-formed data — byte-identical.
- Poll intervals — same cadence, different mechanics.
- The monkey-patch itself (it exists for a reason) — only its observability changes.

## Tests first (TDD)

- `tests/frontend/test_no_silent_excepts.py::test_no_bare_except_pass_under_frontend` — AST scan,
  zero tolerance, with a dated baseline that must drain to empty within this task — structural
- Negative control: planted swallow fails it — control
- `tests/frontend/test_malformed_row_visible.py::test_history_flags_dropped_deal` — malformed
  fixture deal → warning log + visible incomplete marker (not silent omission) — behaviour
- `tests/frontend/test_poll_helper.py::test_fetch_runs_off_event_loop` — loop-blocking probe — behaviour
- `tests/frontend/test_nicegui_canary.py::test_patched_internals_exist` — every attribute
  `app.py:15-59` patches exists with the expected shape — structural canary

## What to do

1. Write the tests; the AST scan must count 31 today (calibration + failure for the right reason).
2. Build the `poll` helper in `components/`; migrate the 33 timers page by page.
3. Replace the 31 swallows with log+marker; history.py first (it lies about money).
4. Canary test for the monkey-patch.
5. `python -m tools.checks all`.

## Where

- `frontend/pages/*` — swallows + timers
- `frontend/components/` — the poll helper
- `frontend/app.py:15-59` — canary target (file itself unchanged)

## Acceptance

- AST scan at zero; loop-probe green on every migrated page; canary red if NiceGUI internals
  rename (demonstrated by pointing it at a fake name — negative control).
- `python -m tools.checks all` green, output pasted into PROGRESS.md.
