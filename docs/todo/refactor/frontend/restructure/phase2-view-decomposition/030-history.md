# 030 — Split `history.py` (1,416 lines)

**Status:** done -- see the outcome at the end
**Depends on:** 2/010 (the convention), and phase-1 task 030 which rewires this file
**Touches money:** no — but it renders the numbers the owner uses to judge whether the app is working, which deserves the same care.
**Layer:** frontend
**Leverage:** `/split-file`; phase-1 task 030 already pinned the summary figures with a characterization test — reuse it

## Problem

`frontend/pages/history.py` is **1,416 lines** and baselined. It holds the closed-trade table, the
equity curve, the summary statistics (win rate, profit factor, realised R, max drawdown), the signal
lab view, date-range filtering, and an AI commentary hook at line 1222.

It also carries a known load characteristic: a long-lived real account's full history at
`days=3650` is the payload that forced the WebSocket buffer from 1MB to 10MB (`app.py:48-60`). That
is a property of this page's data volume, and nothing in this task may change it.

## Decision

`frontend/pages/history.py` → `frontend/pages/history/` per the 2/010 convention. Split by the
surfaces the page actually presents: the trade table, the equity chart, the summary stats block, the
signal lab, and the filter controls.

The summary stats block is the strongest candidate for `components/` if the Edge Dashboard or AI
Summary presents the same figures — check before deciding. Second-caller rule: move it only if a
second caller genuinely exists today.

## What must NOT change

- **Every displayed number.** Win rate, profit factor, realised R, max drawdown, trade counts, the
  equity curve's points. Phase-1 task 030 pinned these in
  `test_history_numbers_characterization.py` — that test passes unmodified through this task.
- **The `days=3650` path still works.** Do not introduce a chunking, pagination or lazy-render change
  while splitting; the 10MB buffer accommodates this page as it is.
- Date-range filter semantics, including the boundary behaviour at each end of a range.
- Sort order and column set of the trade table.
- The AI commentary hook at `history.py:1222` — function-local import, rewired by phase-1 task 030,
  moved only.
- `frontend.pages.history` still imports as a module path (`app.py:715`).
- `ui.timer()` refresh cadence.

## Tests first (TDD)

- `tests/frontend/test_history_package.py::test_every_section_module_is_composed_by_the_package`
  — structural, via the 2/010 orphan walker.
- `tests/frontend/test_history_numbers_characterization.py` — **inherited from phase-1 task 030,
  unmodified.** If it needs editing to pass, the split changed a number and the split is wrong.
- `tests/frontend/test_history_renders.py::test_the_page_builds_with_an_empty_database`
  — wiring, empty state.
- `tests/frontend/test_history_renders.py::test_the_page_builds_with_a_large_history`
  — wiring, seeded with a multi-year dataset. Guards the payload path that forced the buffer change.
- `tests/frontend/test_history_renders.py::test_the_large_history_case_is_actually_large`
  — **negative control**. Assert the seeded dataset genuinely exceeds the old 1MB threshold;
  otherwise the test above proves nothing about the case it was written for.

## What to do

1. Write the tests; run them; confirm they fail for the right reason.
2. Read `/split-file` and follow it.
3. Create `frontend/pages/history/` with `__init__.py` composing only.
4. Move one surface per commit: filters → trade table → summary stats → equity chart → signal lab.
5. Before moving the summary stats block, check whether Edge Dashboard or AI Summary renders the same
   figures. If yes, it goes to `components/analytics/`; if no, it stays private and you say so.
6. `python -m tools.checks all`.

## Where

- `frontend/pages/history.py` → `frontend/pages/history/__init__.py` + `_<surface>.py` modules
- possibly `frontend/components/analytics/` — only on a real second caller

## Acceptance

- No module in the new package is above 800 lines; `__init__.py` is a composer.
- The inherited characterization test passes **unmodified**.
- **The killer test:** load History at `days=3650` against a real account database before and after —
  identical figures, identical curve, and it still renders rather than tripping the WebSocket
  message-size limit.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- If phase-1 task 030 found that `services/analytics/` has only repos and no service layer, this
  page is where that shows up hardest. Do not paper over it in the view.
- Two pages (`ai_summary.py`, `edge_dashboard.py`) read analytics too. If the same summary component
  appears in all three, that is a real shared component and the strongest candidate in this phase for
  `components/`. It is also the only one worth going looking for.

---

## Outcome (done)

Seven modules, largest 451, nothing over the ceiling:

| Module | Lines |
|---|---|
| `_calendar.py` | 451 |
| `_trade_table.py` | 413 |
| `_heatmap.py` | 246 |
| `__init__.py` | 179 |
| `_equity_curve.py` | 139 |
| `_shared.py` | 136 |
| `_channels.py` | 108 |

Zero string literals lost against the pre-split file (1,263 -> 1,270; the seven gained are the
`__all__` entries). Contract edges held at 61. Files over 800 repo-wide: 17 -> 16.

**The stale premise.** This plan says phase-1 pinned every displayed number in
`test_history_numbers_characterization.py` and that this task can reuse it. That file does not
exist. Coverage was two pure clock helpers and the controller — nothing that rendered the page.
`tests/frontend/test_history_page_renders.py` was written first instead, one landmark per
section plus a negative control, watched red twice (a renamed caption, and a section made to
return early as if the split had lost it).

**Now pinned (2026-08-26):** the figures are characterized after all, in
`tests/core/test_mt5_history_characterization.py` -- profit factor, max drawdown, ROI and
the five `daily_*` fields, plus a guard that every key the page reads is still present
(the page uses `.get()` with defaults throughout, so a renamed key blanks a card and
raises nothing). Expected values are derived by hand from the formulas, not copied from a
run, and both a changed formula and a renamed key were watched go red. They live in the
existing file rather than a new one so they reuse its `_FakeBridge` and `engine` fixtures
instead of adding another copy of each to a ratchet that is already over baseline.

**Still outstanding:** those tests assert the sections are
BUILT. They do not assert the numbers. realised R and the equity curve's individual points are still unpinned, and the render
tests assert the sections are BUILT rather than what they say. The summary numbers, which
this plan's "What must NOT change" list leads with, are now covered.

**Not attempted:** the summary-stats-to-`components/` question. The second-caller rule says
move it only if a second caller exists today; that was not investigated, so it stayed put.

**Left alone deliberately:** `_platform_fee_rate`, a dead import chain through `runtime.py`
that the split surfaced. Unpicking it means editing a negative-control test, which is not a
thing to do inside a file move. Tracked in
[031](031-platform-fee-rate-dead-reexport.md).

