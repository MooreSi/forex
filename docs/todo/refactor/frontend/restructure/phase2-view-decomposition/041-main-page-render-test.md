# 041 — A render test for `main_page`, so the app shell can be split

**Status:** not started
**Blocks:** 040 (app shell split) — `frontend/app/__init__.py` is stuck at 1,288 lines
**Touches money:** no
**Layer:** frontend

## Problem

`frontend/app.py` became `frontend/app/` and the About tab moved out, taking it from
1,746 to 1,288 lines. The rest cannot follow.

What remains is `main_page`, the single `@ui.page('/')` route, at 1,101 lines. The pieces
that could be lifted without redesign — `_on_tab_change` (52 lines, closes over nothing),
`_do_env_switch` (114, closes over 11), four dialogs — total roughly 350 and land at ~940.
Still over the ceiling.

The only seam that gets under 800 is the header: a 365-line inline `with ui.row()` block
plus `_refresh_header`, which closes over 27 names (every widget in the bar, plus the price
history, news window and deposit-tracking state). Extracting it means turning inline
construction into a `build_header(...)` that returns its refresh callable. That is a
restructure, and `docs/system/rules/70-file-organisation.md` does not allow one here
without tests.

## Why it is blocked, specifically

Nothing renders `main_page`.

- `tests/frontend/test_pages_render.py` — by its own docstring, "an import-and-signature
  check rather than a full render". It deliberately does not build a NiceGUI client slot.
- `tests/frontend/test_app_boots.py` — starts the app and fetches `/`, but says out loud
  that on an unlicensed checkout `enforce()` serves the **activation screen** and the
  dashboard never renders.

Both are honest about their limits. Between them, a header rebuilt wrongly — a widget that
stops updating, a badge wired to the wrong value — passes green. That is exactly the
failure mode a header extraction has.

## What to do

1. Decide how a test gets a rendered dashboard. Two candidates, neither free:
   - Give the boot test a licensed sentinel so `/` serves the dashboard rather than the
     activation screen, then assert on the served HTML. Touches the licence gate, so read
     `docs/system/domains/` for it first and do not weaken `enforce()`.
   - Build a NiceGUI client slot context in-process and call `main_page()` directly. The
     existing render test rejected this as "testing NiceGUI more than this app" — that
     judgement may still hold.
2. Whichever it is, the test must fail for the right reason before it passes: break a
   header widget deliberately and watch it go red. A render test that cannot see a dead
   badge is worth nothing here.
3. Then, and only then, extract the header per `/split-file`.

## Acceptance

- A test renders `main_page` and asserts on the header's contents.
- A deliberately broken header makes it fail.
- `frontend/app/__init__.py` under 800 lines; `python -m tools.checks all` no worse.
