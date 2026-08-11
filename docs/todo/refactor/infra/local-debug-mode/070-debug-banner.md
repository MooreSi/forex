# 070 — Debug banner

**Status:** not started
**Depends on:** 010-debug-config.md (ships with 060 — same `frontend/app.py` header area)
**Touches money:** no
**Layer:** frontend
**Leverage:** header row `frontend/app.py:889-911`; theme in `frontend/theme.py`; copy + states
in [BAR.md](BAR.md)

## Problem

Debug mode makes every number on screen fake. Without an unmissable, undismissable marker,
someone (including future-Darren, including Simon trying it out) will read a simulated balance
or a fake fill as real. The user asked for exactly this: "a clear banner message at the top".

## Decision

`frontend/components/debug_banner.py` (per frontend conventions): a full-width amber strip
rendered **above** the 54px ticker row and on the login page, driven solely by
`config.is_debug()` — never inferred from data. Copy and the details-popover per BAR.md (which
must be `agreed` before building). Not dismissible, no toggle in the UI.

## What must NOT change

- Header layout/behaviour with debug off — pixel-identical (no wrapper divs that shift it).
- No frontend → `backend.src.db` import; the flag comes through config (or an existing
  controller if conventions demand — check `/frontend-conventions` first).

## Tests first (TDD)

- `tests/frontend/test_debug_banner.py::test_banner_rendered_in_debug` — banner element + exact
  copy present — wiring
- `::test_banner_absent_when_debug_off` — negative control pair
- `::test_banner_driven_by_flag_not_data` — with debug off and the fake bridge somehow active
  (simulated), banner still absent — proves the source of truth is the flag (structural intent;
  implement as a unit test on the render condition)

## What to do

1. BAR.md `agreed` (with 060).
2. Write the tests; watch them fail.
3. Build the component; mount above the header row and on the login page.
4. `python -m tools.checks all`.

## Where

- `frontend/components/debug_banner.py` — new
- `frontend/app.py` — one mount line above `:893` (do not grow this file further)

## Acceptance

- Debug boot: banner on every tab and on the login page; debug off: DOM identical to today.
- **The killer test:** the rendered/absent pair.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

If the suite has no frontend-test idiom yet (check `tests/` first), the render condition lives
in a small pure function so it is unit-testable without NiceGUI; say which route was taken in
PROGRESS.md.
