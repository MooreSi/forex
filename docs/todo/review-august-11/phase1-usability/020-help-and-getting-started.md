# 020 — Help button → Getting Started

**Status:** not started · **Depends on:** BAR.md agreed · **Touches money:** no · **Layer:** frontend

## Problem

The app has genuinely good help (Setup Instructions, Orchestration, a 40-term Glossary) but it is
buried behind the last tab's nav cards (app.py:268-700) with no Help button anywhere and nothing
linking to it. A newcomer never finds it.

## Tests first (TDD)

- `tests/frontend/test_help.py::test_help_button_present_on_shell` — the header renders a "?" help
  control — surface (+ negative control: remove it, test fails)
- `::test_getting_started_links_the_existing_docs` — the Getting Started page references the existing
  Setup/Orchestration/Glossary sections (by their real ids) — wiring

## What to do

1. Write the tests; watch them fail.
2. Add a header "?" button (in the app shell) opening a Getting Started page/dialog that surfaces the
   existing content (link/pull, don't duplicate). Build the page in `frontend/components/`.
3. `python -m tools.checks all`.

## Where
- `frontend/components/getting_started.py` (new) · a few-line header hook in `frontend/app.py`.

## Acceptance
- A "?" is reachable from every screen; it opens guidance that reaches the existing docs. Green suite.
