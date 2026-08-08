# 060 — Ratchet the LOC baseline down

**Status:** not started
**Depends on:** 2/020, 2/030, 2/040, 2/050 all Done
**Touches money:** no — tooling only
**Layer:** tools/tests
**Leverage:** `tools/refactor_audit/structure_gates.py --update-baseline`

## Problem

`structure_baseline.json` is a shrink-only ratchet, and its own comment states the rule: *"Every
number here may fall and may not rise; a file absent from a section may not appear in it. Regenerate
with `--update-baseline`, and only when the totals have gone DOWN."*

After phase 2 the numbers have fallen, but the baseline still records the old ones. Until it is
regenerated the gate permits every split file to grow straight back to where it started, and the
phase's result is not held by anything.

Today's frontend entries:

| File | Baselined |
|---|---|
| `frontend/app.py` | 1,633 |
| `frontend/pages/ai_trade_analysis.py` | 1,250 |
| `frontend/pages/breakout_panel.py` | 919 |
| `frontend/pages/chart.py` | 839 |
| `frontend/pages/history.py` | 1,416 |
| `frontend/pages/reversal_panel.py` | 804 |
| `frontend/pages/settings.py` | 3,112 |
| `frontend/pages/test_panel.py` | 1,246 |

Files that became packages leave the `loc` section entirely — their `__init__.py` and modules should
all be under 800 and so never enter it.

## Decision

Regenerate the baseline once, at the end of the phase, after verifying every total actually fell.
Then record the surviving exemptions with their reasons, so the next reader knows which entries are
"not done yet" and which are "decided, here is why".

One regeneration, not one per task: `--update-baseline` rewrites the whole file, so running it
mid-phase risks capturing an intermediate state as the new floor.

## What must NOT change

- **No file may newly enter any section.** If a split introduced a module over 800, the split is
  wrong — fix it rather than baselining it.
- The `sql`, `ui_db` and `transaction` sections are untouched by this phase and must be byte-identical
  afterwards. `sql` and `ui_db` stay empty.
- Backend entries (`database.py`, `runtime.py`, the cluster files, `mt5_bridge.py`) are unchanged —
  this pack touched none of them.
- The ratchet's own semantics: shrink-only, regenerate only downward.

## Tests first (TDD)

- `tests/refactor/test_structure_baseline.py::test_no_frontend_file_regressed`
  — structural. Asserts every remaining frontend entry is ≤ its pre-phase value, from a copy of the
  old baseline committed as a fixture.
- `tests/refactor/test_structure_baseline.py::test_the_comparison_notices_a_regression`
  — **negative control**.
- `tests/refactor/test_structure_baseline.py::test_no_file_was_added_to_any_section`
  — the other half of the ratchet's rule, which a totals check alone would miss.

## What to do

1. Confirm 2/020–050 are all Done in PROGRESS.md.
2. Copy the current baseline to a test fixture — it is the "before" the tests compare against.
3. Write the tests; run them; confirm they fail for the right reason.
4. `python -m tools.refactor_audit.structure_gates --check` — read the real totals.
5. **Verify they went down** before regenerating. If any went up, stop: something regressed.
6. `python -m tools.refactor_audit.structure_gates --update-baseline`.
7. Diff the baseline. Every change is a decrease or a removal — no additions, no increases. Paste the
   diff into PROGRESS.md.
8. Collect the exemption reasons recorded by 2/040 and 2/050 (`app.py` if it stayed over, `chart.py`,
   `reversal_panel.py`) and hand them to the phase-3 docs task.
9. `python -m tools.checks all`.

## Where

- `tools/refactor_audit/structure_baseline.json` — regenerated
- `tests/refactor/test_structure_baseline.py` — new tests + the pre-phase fixture

## Acceptance

- Baseline regenerated; the diff shows only decreases and removals.
- `sql` and `ui_db` still empty; `transaction` unchanged; backend entries unchanged.
- Files that became packages no longer appear in `loc`.
- Surviving over-800 entries each have a written reason handed to phase 3.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- **Do not lower a ratchet to get CI green** — CLAUDE.md lists it under "Do not". This task is the
  legitimate opposite: recording that the numbers genuinely fell. The difference is entirely in step
  5, and step 5 is the task.
- If `app.py` is still over 800 after 2/040, it stays in the baseline at its new lower number with a
  recorded reason. That is the same treatment `runtime.py` got in M4, and it is honest. Removing it
  from the gate's view instead would not be.
