# 030 — AI & analytics → controllers

**Status:** not started
**Depends on:** none — parallel with 010 and 040
**Touches money:** no. AI commentary and analytics are read-and-describe surfaces; nothing here places, closes or sizes a position. **Exception to watch:** `channels/strategy_ai` can *recommend* a strategy for a channel — recommending is not applying, but confirm that in the code before relying on this line.
**Layer:** frontend → controller
**Leverage:** `ai_analysis_controller.py` (30 lines) and `history_controller.py` (150 lines) both exist

## Problem

| File | Line | Import |
|---|---|---|
| `frontend/pages/ai_trade_analysis.py` | 19, 20 | `services.ai.claude_ai`, `services.ai.provider` |
| `frontend/pages/ai_summary.py` | 15 | `services.analytics.read_repo` |
| `frontend/pages/history.py` | 16 | `services.analytics.trade_history_repo`, `signal_lab_repo` |
| `frontend/pages/history.py` | 1222 | `services.ai.provider as _aip` (function-local) |
| `frontend/pages/edge_dashboard.py` | 14 | `services.analytics.edge_stats` |
| `frontend/pages/trading/_strategy_cards.py` | 6 | `services.ai.provider as ai_provider` |
| `frontend/pages/settings.py` | 772, 867 | `services.ai.provider as ai_provider` (function-local) |

`history.py:16` is the one to look at hardest: importing `trade_history_repo` and `signal_lab_repo`
means a **page holds a repo**. It does not trip `frontend-never-imports-the-database` because those
are service-owned repos rather than `backend.src.db`, but it is the same failure one layer up — the
page is choosing its own data access, and every invariant those repos hold (transaction boundaries,
cache invalidation) is enforceable only by convention from there.

## Decision

Two controllers, split by what the page is asking for rather than by service directory:

- **`ai_analysis_controller`** gains provider selection, model listing and the Claude call surfaces —
  everything `ai.provider` and `ai.claude_ai` are reached for today.
- **`history_controller`** gains named read functions for the analytics repos. Each one names the
  question the page is asking ("closed trades for the last N days", "signal lab rows for channel X"),
  not the repo.

The controller must not receive a repo handle. `controllers-never-import-repos` is enforced at zero
and this task must not be the thing that breaks it — the named function lives on the **service**, and
the controller forwards to it. If `services/analytics/` has no such function, add it there.

## What must NOT change

- **`history.py`'s numbers.** Trade counts, realised R, win rate, profit factor, drawdown and the
  equity curve are identical before and after. These are the figures the owner reads to judge whether
  the app is working; a silent change here is worse than a crash.
- The AI provider fallback chain. If Claude is unreachable today and the app degrades a particular
  way, it degrades that same way after.
- Model IDs and the `_CLAUDE_ALIASES` migration in `run.py:128-164` — untouched.
- Function-local imports at `history.py:1222`, `settings.py:772` and `settings.py:867` stay
  function-local.
- `controllers-never-import-repos` stays at **zero**. This task is the most likely in the pack to
  break it — check the gate after every commit, not just at the end.
- **`history_controller` must stay under 200 lines.** It is at 150, so this task has **50 lines of
  headroom** — the tightest in the phase. The ceiling is enforced at zero with no baseline, and
  splitting the controller into a package is also rejected. If the reads won't fit, that means the
  page is asking several small questions where it should ask one: design a coarser service function
  around the page's actual question. Do not solve it in the controller.
- Existing tests in `tests/services/` and `tests/controllers/` pass unmodified except for mock-target
  relocations.

## Tests first (TDD)

- `tests/controllers/test_history_controller_reads.py::test_each_read_returns_the_same_rows_as_the_repo`
  — surface, against a seeded in-memory DB. One case per new function.
- `tests/controllers/test_history_controller_reads.py::test_the_comparison_notices_a_missing_row`
  — **negative control**. A "same rows" assertion that cannot see a dropped row proves nothing.
- `tests/controllers/test_no_controller_holds_a_repo.py::test_new_functions_take_no_repo_argument`
  — structural. Complements the existing contract by catching a repo passed *as an argument*, which
  an import-based check cannot see.
- `tests/frontend/test_ai_pages_wiring.py` — wiring, one case per rewired call site.
- `tests/frontend/test_ai_pages_wiring.py::test_wiring_detects_a_wrong_provider` — **negative
  control**.
- `tests/frontend/test_history_numbers_characterization.py::test_summary_figures_are_unchanged`
  — characterization against a fixed seeded dataset, pinning win rate, profit factor, realised R and
  max drawdown to exact values. Written **before** anything moves.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason (the characterization one
   should pass — pin it first, then move code).
2. Add named read functions to `services/analytics/` where the page's question has no home yet.
3. Extend `history_controller` with forwarding functions; extend `ai_analysis_controller` likewise.
4. Rewire, one file per commit: `edge_dashboard.py`, `ai_summary.py`, `ai_trade_analysis.py`,
   `history.py`, then the two `settings.py` sites.
5. `_strategy_cards.py:6` — take it if task 020 has not already; note in PROGRESS.md which task did.
6. Check `import_contracts --check` **and** `structure_gates --check` after each commit.
7. `python -m tools.checks all`.

## Where

- `backend/src/services/analytics/` — named read functions, where missing
- `backend/src/controllers/history_controller.py`, `ai_analysis_controller.py` — forwarding functions
- `frontend/pages/history.py`, `ai_summary.py`, `ai_trade_analysis.py`, `edge_dashboard.py`, `settings.py`
- `frontend/pages/trading/_strategy_cards.py:6` (coordinate with 020)

## Acceptance

- No frontend file imports `services.analytics` or `services.ai`.
- No controller imports or receives a repo; `controllers-never-import-repos` still at zero.
- **The killer test:** open History with a real database, note win rate, profit factor and max
  drawdown, apply the change, reopen — the three figures are identical to the digit.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- `history.py` is also a phase-2 split target (1,416 lines). Do the rewiring first and the split
  second — rewiring a file mid-split doubles the review surface for no benefit.
- If `services/analytics/` turns out to have no service layer at all, only repos, say so in
  PROGRESS.md before writing one. That is a bigger finding than this task assumes and the owner
  should hear about it rather than have a service layer invented under it.
