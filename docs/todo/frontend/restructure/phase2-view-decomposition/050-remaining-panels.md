# 050 — Split the remaining oversized panels

**Status:** not started
**Depends on:** 2/010 (the convention). Q2 governs `chart.py` specifically.
**Touches money:** no. The panels start and stop signal engines; they do not place orders.
**Layer:** frontend
**Leverage:** `/split-file`; whatever `components/` gained in 2/020–040

## Problem

Five files remain on the `loc` baseline after 020–040:

| File | Lines | Nature |
|---|---|---|
| `frontend/pages/ai_trade_analysis.py` | 1,250 | AI commentary on individual trades |
| `frontend/pages/test_panel.py` | 1,246 | the Bounce engine panel |
| `frontend/pages/breakout_panel.py` | 919 | the Breakout engine panel |
| `frontend/pages/chart.py` | 839 | ECharts price chart — **39 over; see Q2** |
| `frontend/pages/reversal_panel.py` | 804 | the Reversal engine panel — **4 over** |

The three engine panels are near-identical in structure: engine status, start/stop controls, circuit
breaker state, statistics, recent signals. That duplication is **noted but explicitly out of scope**
(see the pack README) — collapsing them into one parameterised component is a behaviour-risk change
wearing a restructure's clothes, and the three engines have genuinely different semantics underneath
similar-looking controls.

`reversal_panel.py` at 804 is 4 lines over. Splitting a file for 4 lines is exactly the cosmetic
line-chasing FINISH_LINE.md M2 warned about.

## Decision

- **`ai_trade_analysis.py` and `test_panel.py`** → packages per the 2/010 convention. Both are
  comfortably over and have real internal structure.
- **`breakout_panel.py`** → package. At 919 it is 119 over with genuinely separable sections.
- **`chart.py`** → per Q2. Default: **leave it**, record a deliberate exemption with the reason
  (largely one ECharts config; separating it from its consumer for 39 lines is artificial).
- **`reversal_panel.py`** → **leave it.** 4 lines over. Record the exemption. If the three panels
  ever do get unified, it disappears on its own.

The three panels *do* share the shape of their controls. If splitting `test_panel` and
`breakout_panel` produces two near-identical `_controls.py` modules, that is a real second caller and
the shared parts may go to `components/engines/` — **as long as the shared component takes no
engine-specific branching.** The moment it needs `if engine == "breakout"`, stop: that is the
out-of-scope unification arriving by the back door.

## What must NOT change

- **Engine start/stop semantics**, per panel, including the circuit-breaker state display and its
  reset. Phase-1 task 010 routed these through `engines_controller`; this task moves code only.
- **Run Now / Reset behaviour**, and the fact that when the VPS is the active node these buttons act
  on the VPS rather than the local stood-down copy.
- Displayed statistics per engine, to the digit.
- `chart.py`'s ECharts configuration — every option, if it is touched at all.
- The AI commentary shown in `ai_trade_analysis.py`: same prompts, same model selection, same
  fallback when the provider is unreachable.
- `ui.timer()` refresh cadences.
- All five module import paths (`app.py:715-719` imports several directly).

## Tests first (TDD)

- `tests/frontend/test_panel_packages.py::test_every_panel_module_is_composed_by_its_package`
  — structural, via the 2/010 orphan walker.
- `tests/frontend/test_engine_panels_render.py::test_each_panel_builds_in_running_and_stopped_states`
  — wiring, six cases (three engines × two states).
- `tests/frontend/test_engine_panels_render.py::test_the_render_check_notices_a_missing_control`
  — **negative control**.
- `tests/frontend/test_ai_trade_analysis_renders.py::test_the_page_builds_with_and_without_a_provider`
  — wiring, including the provider-unreachable path.
- If any shared component lands in `components/engines/`:
  `tests/frontend/test_shared_engine_components.py::test_the_shared_control_takes_no_engine_branch`
  — structural. AST-asserts no engine-name conditional. This is the guard that keeps the
  out-of-scope unification out.

## What to do

1. Confirm Q2's answer, or proceed on its default and say so in PROGRESS.md.
2. Write the tests; run them; confirm they fail for the right reason.
3. Split `ai_trade_analysis.py` (independent — do it first, no shared-component question).
4. Split `test_panel.py`, then `breakout_panel.py`, one commit each.
5. Only after both: check whether a genuinely branch-free shared component fell out. If yes, move it
   to `components/engines/`. If no, leave both private and say so.
6. Leave `reversal_panel.py` and (per default) `chart.py`; write both exemption reasons into
   PROGRESS.md for the phase-3 docs task to collect.
7. `python -m tools.checks all`.

## Where

- `frontend/pages/ai_trade_analysis.py` → `frontend/pages/ai_trade_analysis/`
- `frontend/pages/test_panel.py` → `frontend/pages/test_panel/`
- `frontend/pages/breakout_panel.py` → `frontend/pages/breakout_panel/`
- `frontend/components/engines/` — only on a genuine, branch-free second caller
- `frontend/pages/chart.py`, `reversal_panel.py` — unchanged, exemptions recorded

## Acceptance

- The three split packages have no module above 800 lines; each `__init__.py` composes.
- Any shared engine component contains no engine-name conditional — proven by test.
- Exemption reasons for `chart.py` and `reversal_panel.py` recorded in PROGRESS.md.
- **The killer test:** start, run-now, reset and stop each of the three engines from its own panel;
  statistics and circuit-breaker state identical to before. Then, with a paired VPS active, confirm
  the buttons still act on the VPS rather than the local copy.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- The temptation to unify the three panels will be strongest here, right after reading all three in
  a row. It is out of scope for a reason: they look alike and behave differently, and the pack that
  proves that is a different pack. Write down what you notice — a future spec starts from it.
- `test_panel.py` is the Bounce engine despite the name. Do not rename it in this task; a rename is a
  separate, easily-reviewed commit and mixing it in obscures the split.
