# 030 — Tab subtitles / plain renames

**Status:** not started · **Depends on:** BAR.md agreed (names are Darren's) · **Touches money:** no · **Layer:** frontend

## Problem

The 10 top-level tabs are jargon with no subtitles (app.py:1507-1516): Parsing, Signal Generator,
Edge, Analysis… A non-expert can't map any to intent.

## Tests first (TDD)

- `tests/frontend/test_tab_labels.py::test_every_tab_has_a_subtitle_or_plain_name` — each tab config
  carries a non-empty subtitle/plain label — surface (+ negative control: blank one, test fails)

## What to do

1. Take the agreed names/subtitles from BAR.md (Darren fills them).
2. Add a subtitle field to the tab definitions and render it; or rename per BAR. No behaviour change.
3. `python -m tools.checks all`.

## Where
- `frontend/app.py` tab definitions (data only — do not grow logic).

## Acceptance
- No tab is an unlabelled jargon word; labels match the agreed BAR. Green suite.
