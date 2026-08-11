# 050 — About reframed: "Set up once / Every day"

**Status:** not started · **Depends on:** 010-040 (reuses the components) · **Touches money:** no · **Layer:** frontend

## Problem

The About-home is an encyclopedia (install-focused nav cards) not a path. A user can't tell what is
one-time setup vs daily use.

## Tests first (TDD)

- `tests/frontend/test_about_home.py::test_about_groups_setup_and_daily` — the About home renders two
  groups, "Set up once" and "Every day", each populated from the existing content — surface

## What to do

1. Write the test; watch it fail.
2. Regroup the existing About nav cards (app.py:268-700 content) into the two buckets; no new prose
   needed — reuse the good content that exists. Build as a component, not inline growth.
3. `python -m tools.checks all`.

## Where
- `frontend/components/about_home.py` (new) · the About page render.

## Acceptance
- About reads as a path (set up once → every day), using existing content. Green suite.
