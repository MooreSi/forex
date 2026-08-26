# 010 — "Reset to defaults" on the signal test panel raises NameError

**Status:** not started — **and it blocks the test_panel split**
**Found:** 2026-08-26, while splitting `frontend/pages/test_panel.py`
**Touches money:** no — it is the bounce/test panel's parameter block, not an order path
**Severity:** live, user-facing, and silent until clicked

## What happens

`frontend/pages/test_panel/__init__.py` (was `test_panel.py:765`):

```python
def _reset_params():
    ap.reset_to_defaults()
    asyncio.create_task(_render_ap())
    ui.notify("Parameters reset to defaults", type="info")
```

`ap` is not bound anywhere in the module. It is the only occurrence of that name in
the file — before the split and after it. Clicking **Reset to defaults** raises
`NameError: name 'ap' is not defined`; the handler dies before the notify, so the
user sees nothing happen at all.

`pyflakes` has been reporting it all along:

```
frontend/pages/test_panel.py:765:29: undefined name 'ap'
```

Pre-existing, not introduced by the package split, and left exactly where it was
rather than guessed at.

## Likely cause

The sibling renderer `_render_ap` closes over `ap` and `ap_area`, so `ap` was almost
certainly a local in an enclosing scope that was renamed or removed. Check
`engines_controller.bounce` for a params object carrying `reset_to_defaults()`.

## What to do

1. Find what `ap` was — do not invent a replacement. If the params object is reachable
   through the controller, bind it the way `_render_ap` does.
2. Test first: render the panel, invoke the reset handler, assert it does not raise and
   that the notify fires. `tests/frontend/conftest.py` has the render harness.
3. Check the breakout and reversal panels for the same pattern — they share this shape.

## Note

Worth asking why this was never noticed: either the button has not been used, or it has
and the failure was invisible. If the latter, other handlers on these panels may be
failing the same silent way.

## Why this blocks the split

`frontend/pages/test_panel.py` was split into a package and the split was **reverted**.

`tests/frontend/test_page_packages_are_wired.py` resolves every global name a page
PACKAGE uses, statically, across branches no test executes. It is enforced at zero and
has no allowlist — deliberately, because its whole purpose is this class of bug. A flat
module is not subject to it; a package is. So the moment `test_panel.py` became
`test_panel/`, the gate went red on `ap` and the suite gained an eighth failure.

The split itself was clean — 1,245 lines to 647/569/72, zero string literals lost — but
it is not worth leaving a gate red, and the alternative was worse: making the button work
means adding `reset_adaptive_params()` to `engines_controller.bounce`, because the page
may not import `backend.src.services.test_signal.adaptive_params` directly (the
frontend-through-controllers contract). That is new controller surface and it turns a
dead button live on a signal-generation panel — not a change to make unattended, and not
a change to bury inside a file move.

**Fix this first, then re-run the split.** The split recipe that worked: lift
`_render_ml` (259 lines), `_render_history` (156) and `_render_active` (130) out of
`_render_main` — each closes over exactly one name, its container — and move the seven
formatting helpers plus `_ml_thresh` into `_shared.py` so `_sections.py` need not import
back out of the package.

