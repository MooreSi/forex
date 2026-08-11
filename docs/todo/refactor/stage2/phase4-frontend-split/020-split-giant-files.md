# 020 — Split settings.py / history.py / app.py

**Status:** not started · **Depends on:** 010 (restructure conventions) · **Touches money:** no · **Layer:** frontend
**Leverage:** `/split-file` (package-dir split preserving import path); the review found clean
`_render_*` seams in settings.py for a ~9-module split.

## Problem

`settings.py` 3,112 lines, `history.py` 1,416, `app.py` 1,633 — all over the 800 gate, hard to
navigate, and where duplicated helpers and silent excepts accumulate.

## Tests first (TDD)
- Structural: `tests/refactor/test_structure_gates.py` LOC gate shows each split file under 800 after;
  the frontend page-render tests still pass unmodified (behaviour preserved by verbatim moves).
- Any extracted shared helper (`_fmt_ts`/`_dir_color`/`_pnl_color`/`_safe_refresh`) gets one home in
  `components/` with a test; the drifted copies are removed.

## What to do
1. `/split-file` settings.py into `frontend/pages/settings/` at the `_render_*` seams (verbatim moves).
2. Same for history.py and app.py where seams exist; seed `components/` with the shared helpers.
3. Keep behaviour byte-identical (render tests unmodified). `python -m tools.checks all` per split.

## Where
- `frontend/pages/settings/` (new package) · history.py, app.py · `frontend/components/`.

## Acceptance
- No frontend/pages file over 800 lines; shared helpers de-duplicated into components/; render tests
  pass unmodified. Green suite.
