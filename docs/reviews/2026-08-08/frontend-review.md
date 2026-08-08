# Frontend review — 2026-08-08

Read-only inspection of `frontend/` (NiceGUI, 17,848 lines across 31 Python files) against
`docs/specs/001-frontend-restructure.md`, the plan pack at `docs/todo/frontend/restructure/`,
CLAUDE.md and the `docs/system/rules/` conventions. No code was modified; no app was run. The one command
executed against the repo was the read-only gate `python -m tools.refactor_audit.import_contracts --check`.

## Summary

The 001 restructure spec is a good, honest plan — and **none of it has started**. Two days after
the pack was scaffolded (2026-08-06), the contract it exists to close still reads
**`frontend-reaches-the-backend-through-controllers: 59 violation(s), baselined`** (verified today),
`frontend/components/` is still empty (`frontend/components/__init__.py` is 0 bytes), every row in
`docs/todo/frontend/restructure/PROGRESS.md` is `not started`, and the four owner questions in
QUESTIONS.md are unanswered — which already blocks phase-2 task 040 (app shell).

The good news the spec relies on is real: the database boundary **is** closed (zero
`backend.src.db` imports anywhere under `frontend/`, contract enforced at zero), and
`frontend/pages/trading/` genuinely demonstrates the target package shape (slim
`__init__.py`, 10 `_*.py` section modules). The bad news is also real: ~35 controller imports
coexist with ~50+ direct service/config-internal imports, `settings.py` is a 3,112-line
monolith that embeds subprocess/process management in the view layer, three engine panels carry
near-identical copy-pasted helper sets, 31 `except Exception: pass` blocks silently swallow
errors in UI callbacks, and frontend test coverage is 3 smoke/wiring files (~330 lines, 11
tests) for 21 page modules. `frontend/tests/` itself contains only an empty `__init__.py` —
the real tests live in `tests/frontend/`.

## Restructure spec status

### What the spec calls for

- **Phase 1** — drive `frontend-reaches-the-backend-through-controllers` from 59 → 0, add
  `notifications_controller` and `backtest_controller` where none fits, then flip
  `enforced_at_zero=True`. Task 020 (trading & risk) is money-touching: `/safe-change`, owner
  sign-off, demo session, ships alone.
- **Phase 2** — populate `frontend/components/<domain>/` on the `pages/trading/` pattern; split
  `settings.py` (3,112), `history.py` (1,416), `app.py` (1,633), and the remaining oversized
  panels; ratchet the LOC baseline down.
- **Phase 3** — document conventions in `docs/system/rules/` and record the React/Next.js rejection.
- **Invariants**: byte-identical behaviour, four zero-contracts stay at zero, close path frozen,
  function-local deferred imports at `app.py:982/1127/1246` stay function-local, baselines only shrink.

### What is actually done

| Item | Spec target | Current state | Evidence |
|---|---|---|---|
| Service-boundary contract | 0, enforced | **59, baselined** — unchanged since scaffold | `import_contracts --check`, run 2026-08-08 |
| DB boundary | stays at 0 | at 0 (holds) | same gate: `frontend-never-imports-the-database: enforced at zero` |
| `notifications_controller`, `backtest_controller` | created | not created; pages import `backend.src.services.notifications` / `backend.src.services.backtest` directly | `frontend/pages/settings.py:1238,1265,1361,1697`; `frontend/pages/backtest.py` |
| `frontend/components/<domain>/` | populated | **empty** — `components/__init__.py` is 0 lines | `frontend/components/` |
| `settings.py` split | package of components | still one 3,112-line file | `frontend/pages/settings.py` |
| `history.py` / `app.py` / panels split | packages | untouched: 1,416 / 1,633 / 1,250 / 1,246 / 919 / 839 / 804 | `wc -l` |
| Phase 3 docs | written | not started; `docs/system/rules/` unchanged (8 files, no frontend-conventions addition) | `docs/todo/frontend/restructure/PROGRESS.md` |
| Owner questions | answered | **0 of 4** — task 2/040 explicitly blocked on Q1 | `PROGRESS.md:22,69-70` |
| Verification checklist | filled | all boxes unchecked | `docs/specs/001-frontend-restructure.md:177-188` |

**Net: 0 of 13 tasks started.** The invariants have at least not regressed: the deferred
function-local imports the spec pins are still function-local (`frontend/app.py:982`, `:1127`,
`:1246`), the close path is untouched, and the DB contract holds. The only progress metric the
pack asks agents to update — the contract-count table in PROGRESS.md — still shows only the
2026-08-06 scaffold row of 59, which today's run confirms is accurate. PROGRESS.md is honest.

## Findings

### High

**H1 — The service boundary is wide open, including on money-adjacent paths.**
59 baselined violations (verified today). Distribution of `backend.src.services/app/runtime`
imports by file: `settings.py` 9, `app.py` 7, `trading/_strategy_cards.py` 5, `history.py` 4,
`trading/_manual_entry.py` 3, `remote_node.py` 3, plus 11 more files. `trading/_manual_entry.py`
and `trading/_strategy_cards.py` sit on the order-entry surface of a live-money app — every direct
service import there is a call site the spec's money-touching task 1/020 must characterise and
reroute under `/safe-change`. Until phase 1 runs, any service-signature change fans out across
17 frontend files with no contract to catch it.

**H2 — `frontend/pages/history.py:16-19` imports repo modules and private runtime internals.**
```python
from backend.src.services.analytics import trade_history_repo, signal_lab_repo
from backend.src.runtime import _apply_fee, _platform_fee_rate
```
This is the worst of the 59: a page binding directly to *repo-named* modules (one naming rename
away from a DB-boundary breach in spirit) and to underscore-private functions of the runtime
composition root. Fee computation (`_apply_fee` used at `history.py:765`) is money math being
performed in a view. These four imports should be at the top of the phase-1/030 or /050 worklist,
and `_apply_fee`/`_platform_fee_rate` need a public controller-exposed surface, not a private hoist.

**H3 — `settings.py` (3,112 lines) is not just oversized; it embeds process management in the view layer.**
Internal outline (all in one file): MT5 credentials (`_render_mt5`, line 150), EA update button
(303), risk card (507), AI provider cards (`_render_ai` 732, `_render_claude_card` 771,
`_render_deepseek_card` 866), Telegram bot (971), email/SMTP (1136), **MT5 bridge control**
(`_render_bridge_control`, 1786 — spawns and tracks `subprocess.Popen` bridge processes, Wine
bottle detection at 1763-1782, `pgrep` at 1964, package install via pip subprocess at 2227),
diagnostics (2283, with its own 5 s live-log timer at 2336), theme (2997), registration (3054).
Module-level mutable process state `_bridge_proc = [None]` / `_bridge_starting = [False]`
(`settings.py:1759-1760`) and `_caffeinate_proc` (`settings.py:19`) mean a UI module owns OS
process lifecycles. Bridge start/stop belongs behind a controller (it starts the process that
talks to MT5 — operationally money-adjacent); the page should render buttons and labels.
This maps directly to spec phase-2 task 020; a split plan is in Recommendations.

### Medium

**M1 — 31 `except Exception: pass` blocks silently swallow errors in UI callbacks and timers**
(108 `except Exception` total under `frontend/`). Examples: `history.py:85-86` (the 15 s
`refresh_perf` poll — if the perf fetch breaks, the header freezes on stale numbers with no log,
no notify), `history.py:223-224`, `252-253`, `707-708`, `767-768` (inside the fee/P&L mapping
loop — a malformed deal is silently dropped from displayed P&L), `1159-1160`, `1256-1257`. In a
live-money dashboard, stale-but-plausible numbers are worse than a visible error. At minimum
these should log; user-facing refreshes should surface a "data stale since …" indicator.

**M2 — 33 `ui.timer` polling loops with no shared pattern and mostly-synchronous bodies.**
Every page rolls its own poll (2 s–60 s): `app.py:1280` (2 s header), `app.py:1551`,
`history.py:88/255/636/1073/1314` (five independent 15–60 s timers on one page),
`chart.py:835-836`, `telegram.py:282` (a 1 s wizard tick), `trading/__init__.py:106`, etc.
Only `ai_trade_analysis.py:679-687` offloads sync DB work via `run_in_executor`;
`breakout_panel.py:901-914` documents that its offload lives in the panel-data service. The rest
run service/repo calls directly on the event loop — `history.py`'s `reload` (timer at 1073)
re-pulls trade history each tick, exactly the payload class the 10 MB websocket patch at
`app.py:50-59` exists to accommodate. One janky poll degrades every connected client. A shared
`poll(interval, fetch, apply)` helper that offloads `fetch` and centralises disconnect/error
handling is a natural first resident of `components/` and would replace ~30 hand-rolled loops.

**M3 — Duplicated helper sets across the engine panels.** `_fmt_ts`, `_fmt_dur(ation)`,
`_dir_color`, `_pnl_color` are re-implemented in `breakout_panel.py:29-59`,
`reversal_panel.py:38-84`, `test_panel.py:32-84`, with `_fmt_ts` again in
`ai_trade_analysis.py:47` — and they have already drifted (breakout's `_pnl_color` guards
`TypeError/ValueError`; reversal adds an `_outcome_color` variant). The `_safe_refresh` +
`add_refresh_callback` + `ui.timer(30, …)` tail is likewise cloned (`breakout_panel.py:901-919`,
`reversal_panel.py:784-804`, `test_panel.py:1234-1246`). The spec rightly defers *merging the
panels* as behaviour-risk, but extracting these pure formatting helpers into
`components/format.py` is drift-free and shrinks all three files. This is precisely the
"components have nowhere to live" problem: `components/` has been empty since creation while
identical code accreted in four pages.

**M4 — `app.py:15-59` monkey-patches NiceGUI internals pinned to 3.12.1 behaviour.**
`Timer._get_context` and `Timer._cleanup` are replaced (`app.py:25-44`), and
`core.sio.eio.max_http_buffer_size` is force-set to 10 MB (`app.py:59`). Both patches are
well-commented and address real bugs, but they reach into private attributes
(`_parent_slot`, `_deleted`, `eio`) that a NiceGUI upgrade can silently invalidate — the timer
patch failing open would restore log spam; failing differently could cancel live timers. There is
no test asserting the patched attributes still exist. A cheap guard: a unit test that fails on
NiceGUI upgrade if `_UITimer._get_context` / `_parent_slot` disappear.

**M5 — Frontend test coverage is boot-smoke only.** `tests/frontend/` holds three files
(`test_app_boots.py` 137 lines, `test_page_packages_are_wired.py` 137, `test_pages_render.py` 58
— 11 tests total) against 21 page modules / 17,848 lines. Coverage is: app boots, pages import,
each page exposes a renderer, package names resolve. There are zero behavioural tests for
settings persistence, history rendering, manual entry, or any dialog. The spec's test plan
(characterisation + wiring + negative controls, `docs/specs/001-frontend-restructure.md:123-141`)
is the right prescription and none of it exists yet — which is expected pre-phase-1, but it means
today the restructure has no safety net to move code over. Also, `frontend/tests/` (the in-package
directory) contains only an empty `__init__.py`; it is a decoy. Either move `tests/frontend/`
content there or delete it so there is one obvious location.

### Low

**L1 — Module-level mutable state instead of per-client storage.** Beyond the process boxes in
H3, pages hold cross-request state in module globals (e.g. `settings.py:1759-1760`,
`_diag_refresh_timer = [None]` at `settings.py:89`, history's `_state` month cursor). Zero uses of
`app.storage` anywhere in `frontend/`. For a single-user localhost dashboard this mostly works,
but two open browser tabs share month-navigation and diagnostics-timer state in surprising ways.
Not worth fixing before the restructure; worth a convention line in phase 3.

**L2 — Blocking calls inside async settings handlers.** `settings.py:1925` builds a `Popen` with
`stdout=PIPE` that is only ever `read(4096)` once after exit (`:1945`) — if the bridge stays up
and chats, the pipe buffer eventually fills and can stall the child; `settings.py:1964`
`subprocess.check_output(["pgrep", …])` runs synchronously on the event loop (macOS path, fast,
but a hang in `pgrep` freezes the whole UI). The Windows update path correctly uses
`asyncio.create_subprocess_exec` + `wait_for` (`settings.py:2181-2234`); the bridge path should
match it.

**L3 — `chart.py` at 839 lines.** 39 over the gate, largely one ECharts config. The spec's own
assumption (Open question 2) is to leave it and record a deliberate exemption. Agree — but the
exemption has not been recorded anywhere yet.

**L4 — Per-page `render()` signatures are inconsistent.** `settings.render(get_engine,
get_tg_reader)` (`settings.py:49`), `test_panel.render(get_engine)` (`test_panel.py:95`),
`breakout_panel.render()` (`breakout_panel.py:88`). The engine-getter is threaded through some
pages as a callable and reached via `from backend.src.app import get_engine` in others
(`settings.py:1274`). Phase-2 task 010 (component convention) should pick one and write it down.

## Recommendations (prioritized)

1. **Execute phase 1 before anything else — starting with the money-free lanes.** Tasks 010
   (engine panels), 030 (ai & analytics) and 040 (notifications/telegram) are declared
   independent and parallelisable in the pack README. `history.py:16-19` (H2) should be swept in
   with 030: give `_apply_fee` / `_platform_fee_rate` a named public controller function rather
   than importing runtime privates. Every phase-1 landing must update the PROGRESS.md count
   table — it is currently the only honest metric and it works.
2. **Get the four QUESTIONS.md answers from the owner now.** Q1 already blocks task 2/040, and
   the test-strategy question (boot smoke vs per-package tests) gates how phase 2 is verified.
   Two days of zero movement with 0/4 answered suggests the pack is waiting on a human, not an agent.
3. **Schedule task 1/020 (trading & risk) deliberately**: `/safe-change`, characterisation tests
   against unmodified code first (`test_manual_entry_characterization.py` per the spec), own
   commit, demo session, owner sign-off. Do not let an agent fold it into a sweep.
4. **Split `settings.py` along its existing `_render_*` seams** (they are already clean section
   functions): `components/settings/` with `mt5_credentials.py` (150-506), `risk.py` (507-718),
   `ai_providers.py` (732-970), `telegram_bot.py` (971-1077), `email.py` (1078-1698),
   `bridge_control.py` (1759-2282), `diagnostics.py` (2283-2996), `theme.py` (2997-3053),
   `registration.py` (3054-end), behind a slim tab-composing `__init__.py` mirroring
   `pages/trading/__init__.py`. Separately (not in the pure restructure), move bridge
   process-lifecycle logic behind a controller.
5. **Seed `components/` with the two things already duplicated**: `components/format.py`
   (`_fmt_ts`/`_fmt_dur`/`_dir_color`/`_pnl_color`, M3) and a shared poll/refresh helper (M2)
   that offloads sync fetches and centralises the disconnect-`RuntimeError` handling currently
   copy-pasted in each `_safe_refresh`. Both shrink the panels ahead of task 2/050 without
   touching behaviour-risk panel merging.
6. **Replace `except Exception: pass` in refresh paths with logged, surfaced staleness** (M1) —
   at minimum `log.debug` plus a stale-data indicator on the five `history.py` pollers. This can
   ride with phase-2 splits page by page, but the fee-mapping swallow at `history.py:767-768`
   deserves a look sooner: it can silently under-report displayed P&L.
7. **Add a NiceGUI-upgrade canary test** for the `app.py:15-59` monkey-patches (M4), and record
   the `chart.py` exemption (L3) plus the render-signature convention (L4) in the phase-3 docs.
8. **Resolve the `frontend/tests/` vs `tests/frontend/` split** (M5) — delete the empty decoy or
   consolidate, before phase 2 multiplies the number of files agents must find.
