# Frontend structure & code-quality review — 2026-08-11

Read-only inspection of `frontend/` (NiceGUI, ~19,100 lines across 34 Python files). Context read:
the 2026-08-08 frontend review, today's `frontend-onboarding-review.md` (its onboarding findings are
**not repeated** here — this review covers structure and code quality), and the restructure pack at
`docs/todo/refactor/frontend/restructure/`. One read-only gate was executed:
`python -m tools.refactor_audit.import_contracts --check`. No app run, no tests run, no code changed.

## Summary + verdict

The restructure has finally **started moving, and moving in the right way**. Since the 08-08 review
(0/13 tasks): phase-1 task 010 landed (`engines_controller`, contract **59 → 50**, baseline
tightened, commit `30e1a75`), `components/` gained its **first six real residents** (commit
`9ff9fba` — `start_here.py`, `getting_started.py`, `tab_labels.py`, `empty_state.py`,
`about_home.py`, `debug_banner.py`), the QUESTIONS.md blockers were answered provisionally under the
deferred-questions workflow, the `frontend/tests/` decoy directory is gone, a NiceGUI-upgrade canary
test exists (`tests/frontend/test_nicegui_canary.py`, closing 08-08 M4), and — the standout — a
**silent-except ratchet gate** (`tests/frontend/test_no_silent_excepts.py`) now pins the swallow
count at exactly 40 with a shrink-only baseline and a negative control. The frontend test suite grew
from 3 files/11 tests to **13 test files (~1,900 lines)**.

**Verdict: no longer a monolith wearing a package structure — but still a monolith with a package
structure growing around it.** The new code (auth gate, Start Here, components, the trading package)
is genuinely well-shaped: layered, testable, logged. The old core is untouched: `settings.py` is
still **3,112 lines** and still owns OS subprocess lifecycles from the view layer, `history.py`
still does fee math via runtime privates, format/poll helpers are still copy-pasted across four
panels, and 12 of 13 restructure tasks remain open. A future developer can now maintain the *edges*
of this frontend; the *center* (settings, history, app shell) still requires archaeology. Trajectory
is right; the big files are the remaining risk.

## Previous findings — verification table (re-measured today)

| Metric | 08-08 | 08-11 (onboarding rev.) | Now (this review) | Evidence |
|---|---|---|---|---|
| Restructure tasks done | 0/13 | 0/13 | **1/13** (phase1/010) | `PROGRESS.md` row 1, commit `30e1a75` |
| Controller-boundary contract | 59, baselined | 59 | **50, baselined (tightened)** | `import_contracts --check`, run today |
| DB boundary (`backend.src.db` in frontend) | 0 | 0 | **0 — holds** | grep + gate: `frontend-never-imports-the-database: enforced at zero` |
| `components/` | empty | empty | **6 modules, 534 lines** | `frontend/components/` |
| `settings.py` | 3,112 | 3,112 | **3,112 — unchanged** | `wc -l` |
| `app.py` | 1,633 | 1,633 | **1,605** (shrank via about_home extraction) | `wc -l` |
| `history.py` | 1,416 | 1,416 | **1,415** | `wc -l` |
| `except Exception: pass` | 31 | 44 (regressed) | **40** (AST-exact; now gated at ≤40, shrink-only) | `test_no_silent_excepts.py:20`; my AST count matches |
| `except Exception` total | 108 | 143 | **146** | grep |
| `ui.timer` polls | 33 | 32 | **31** | grep |
| Direct `backend.src.{services,app,runtime,config}` imports | ~59 | 58 | **49 lines across 13 files** | grep; `settings.py` alone has 19 |
| QUESTIONS.md answered | 0/4 | 0/4 | **4/4 provisionally** (Simon reviews at end) | `PROGRESS.md` header, 2026-08-11 |
| `frontend/tests/` decoy | empty `__init__.py` | — | **deleted** | `ls frontend/tests` → gone |
| NiceGUI monkey-patch canary (08-08 M4) | none | — | **exists** | `tests/frontend/test_nicegui_canary.py` |
| Frontend tests | 3 files, 11 tests | — | **13 files, ~1,900 lines** incl. negative controls | `tests/frontend/` |

Note on the 31→44→40 swallow numbers: the three reviews used different counting methods
(regex vs AST). The gate's AST definition (broad except whose body is exactly `pass`) is now the
canonical one, and it asserts the baseline equals the real count (`test_baseline_is_not_slack`) —
the number can only go down from here. Whether real swallows were added between 08-08 and 08-11 or
the 31 was an undercount cannot be settled retroactively; what matters is the ratchet exists.

## Trading package split (commit `33ed04b`) — quality assessment

**Real decomposition, done the right way, in two commits.** `2386b55` converted the 3,254-line file
to a package as a *pure move* (verifiable no-op), then `33ed04b` split it into 11 modules along
section seams, extracting genuinely shared helpers into `_shared.py` (57 lines, pure formatting)
rather than duplicating them. Largest module is now `_strategy.py` at 563 lines. The commit message
honestly documents four things that went wrong (module-level names not following their functions,
raising `NameError` on untested error paths) and the fix: `test_page_packages_are_wired.py`
statically resolves every global each section loads. That test is the reusable safety net the
`settings.py` split needs. Public surface (`render`, `render_signals_card`, labels) was preserved so
`app.py`/`telegram.py`/`chart.py` were untouched. This is the template; it just hasn't been applied
to the three biggest files yet.

## Top 10 largest frontend files (today)

| Lines | File | Over 800-line gate? |
|---|---|---|
| 3,112 | `frontend/pages/settings.py` | yes — 3.9x |
| 1,605 | `frontend/app.py` | yes |
| 1,415 | `frontend/pages/history.py` | yes |
| 1,250 | `frontend/pages/ai_trade_analysis.py` | yes |
| 1,245 | `frontend/pages/test_panel.py` | yes |
| 918 | `frontend/pages/breakout_panel.py` | yes |
| 839 | `frontend/pages/chart.py` | yes (exemption still unrecorded — 08-08 L3) |
| 803 | `frontend/pages/reversal_panel.py` | yes |
| 734 | `frontend/pages/telegram.py` | no |
| 612 | `frontend/pages/backtest.py` | no |

## New findings by severity

### High

**H1 — `settings.py:1759-2282` still runs MT5-bridge process management from the view layer.**
Unchanged since 08-08: module-level `_bridge_proc = [None]` (`settings.py:1759`),
`subprocess.Popen` at `:1925` and `:2042` with `stdout=PIPE` read once after exit (pipe-fill stall
risk), synchronous `subprocess.check_output(["pgrep", "-f", "terminal64.exe"])` on the event loop at
`:1964-1966`, plus `_caffeinate_proc` at `:19`/`:410`. This is the process that talks to MT5 —
operationally money-adjacent — owned by a UI tab. It is also the single biggest reason `settings.py`
has **19 direct backend imports** (worst file in the contract's remaining 50). Phase-2 task 020
exists for this; it is the highest-value open item in the pack.

**H2 — `history.py:17` still imports runtime privates for money math in a view.**
`from backend.src.runtime import _apply_fee, _platform_fee_rate`, used at `history.py:470` and
`:764` to compute displayed net P&L — with a bare swallow at `:766` inside the fee-mapping loop that
can silently drop a malformed deal from displayed P&L (08-08 M1's worst instance, still live). Same
file also imports repo-named modules directly (`history.py:14`). This was H2 in the 08-08 review;
it maps to phase-1 task 030/050 and has not moved.

### Medium

**M1 — Format/poll helper duplication is unchanged; `components/format.py` was never created.**
`_fmt_ts`/`_fmt_dur`/`_dir_color`/`_pnl_color` remain cloned in `breakout_panel.py`,
`reversal_panel.py`, `test_panel.py`, `ai_trade_analysis.py` (grep confirms all four, with drift);
the `_safe_refresh` + timer tail is still cloned in the three engine panels. `components/` was
seeded with onboarding widgets (good) but not with the two extractions both prior reviews said
should go first. Note the *pattern* now exists twice — `trading/_shared.py` holds `_uk`,
`_pnl_colour`, `_pnl_bg` for the trading sections — so there are now **two** partially-overlapping
formatting helper sets plus four page-local ones.

**M2 — 31 `ui.timer` polls remain almost entirely synchronous on the event loop.**
Only `ai_trade_analysis.py` offloads via `run_in_executor` (3 sites). `history.py` still runs five
independent 15–60 s timers whose bodies hit repos/services directly; a shared offloading poll helper
(08-08 M2) still does not exist and `components/` is now the obvious home for it.

**M3 — `components/start_here.py:134-135` and `auth_gate.py:13` import backend controllers from
component/gate modules.** Both are *controller* imports (the correct layer — no violation), but the
components dir is acquiring backend dependencies from day one. `start_here.py` gets it mostly right
(caller passes `demo_mode`; controllers only; every failure logged at `:152-165`, never swallowed).
Worth writing the rule down in phase-3 docs: components may import controllers, never services —
before the next six components are written without a convention.

**M4 — The remaining 49 direct-import lines are concentrated where the risk is.**
Distribution: `settings.py` 19, `app.py` 6, `trading/_strategy_cards.py` 5, `history.py` 5,
`trading/_manual_entry.py` 3, `ai_trade_analysis.py` 3, then a tail of 7 files. The money-touching
lane (phase-1/020: `_manual_entry`, `_strategy_cards` — 8 imports on the order-entry surface)
is still `not started` and correctly quarantined behind `/safe-change` + owner sign-off.

### Low

**L1 — `chart.py` LOC exemption (08-08 L3) still unrecorded** while phase-3 docs remain unstarted;
same for the render-signature inconsistency (08-08 L4): `settings.render(get_engine, get_tg_reader)`
vs `breakout_panel.render()` is unchanged, and `settings.py:1274` still reaches
`backend.src.app.get_engine` directly despite also receiving a getter.

**L2 — `trading/_shared.py` has a nested unreachable-ish except and cramped style** (`_uk` has an
inner `except Exception` swallow returning truncated raw text; single-line `if v > 0:  return`
bodies). Minor, but it is the file the next extractions will copy.

**L3 — PROGRESS.md "Overall" block is stale relative to its own task table**: the header says
phase 1 "not started — contract at 59" while row 010 is `done` at 50 and the header note says
59→50. The count table at the top still shows only the 2026-08-06 row. Cheap fix, and it is the
pack's declared single honest metric.

## What is genuinely healthy

- **The DB boundary is real and holding**: zero `backend.src.db` imports under `frontend/`,
  enforced at zero, third review in a row.
- **The ratchet culture arrived**: `test_no_silent_excepts.py` is exactly the right shape —
  AST-based, baseline pinned to the true count, shrink-only, with a negative control proving the
  detector works. Same spirit as the tightened import-contract baseline (59→50, cannot regress).
- **`auth_gate.py` (67 lines) is a model module**: middleware + two pages, goes through
  `auth_controller`, idempotent install, signed `app.storage.user` cookie, correct open-prefix list,
  referrer preservation, wired from `run.py:333` not sprinkled through `app.py`.
- **`components/start_here.py` is a model component**: pure-view render fed a status dict, testable
  `checklist_rows()`/`should_show()` pure functions, controller-only data access, every fetch
  failure logged and degraded to "not done" instead of swallowed or crashed.
- **The trading split is a reusable template** — pure-move commit, then seam-split commit, plus a
  static wiring test that already caught five real latent `NameError`s.
- **The test suite is no longer decorative**: 13 files including canary, ratchet, wiring, and
  per-component tests with negative controls, watched red-first per the 9ff9fba commit message.
- **PROGRESS.md task rows and the questions workflow are being used honestly** (modulo L3's stale
  header) — the pack is functioning as a coordination surface across agents.

## Top 5 things to strengthen (priority order)

1. **Split `settings.py` using the trading-package template** (phase-2/020), and in the same effort
   move bridge process lifecycle behind a controller (H1). It is 16% of the frontend in one file,
   the worst import offender, and the page every setup step lands on.
2. **Finish phase 1** — 030/040/050 are money-free and drain most of the remaining 50; give
   `_apply_fee`/`_platform_fee_rate` a public controller surface to kill H2's runtime-private
   imports. Schedule 020 (trading & risk) deliberately under `/safe-change` as the pack demands.
3. **Seed `components/format.py` and a shared offloading poll helper** (M1, M2) — the two
   extractions every review has asked for; both shrink four panels with zero behaviour risk, and
   the poll helper is the structural fix for 31 synchronous timers and many of the 40 swallows.
4. **Ratchet the swallow baseline down on a schedule** — the gate stops regression but 40 swallows
   still leave stale-but-plausible numbers on a live-money dashboard with no indicator; convert the
   `history.py` poller/fee-loop ones first (`:84`, `:222`, `:251`, `:706`, `:766`).
5. **Write the phase-3 conventions now, not last**: component/controller import rule (M3), render
   signature (L1), the `chart.py` exemption, and refresh the stale PROGRESS.md header (L3) — cheap,
   and it keeps the healthy new pattern from drifting while the big splits are in flight.
