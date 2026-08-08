# Frontend restructure — phase 1: close the controller boundary

**Status:** not started
**Gated on:** nothing — this phase can start immediately. QUESTIONS.md does not block it.
**Touches money:** YES — task 020 only.

## Goal of this phase

`frontend-reaches-the-backend-through-controllers` goes from **59 to 0** and is flipped to
`enforced_at_zero=True`, joining the four contracts already held at zero. After this, `frontend/`
reaches the backend through `controllers/` and nothing else, enforced by the suite rather than by
convention.

Nothing the app does changes. Every task is a rewiring: the same service function is called with the
same arguments, reached through a controller instead of directly.

## The rule every task follows

From CLAUDE.md: *a controller is a flat `<name>_controller.py` that names an operation and forwards
it to one service — no loops, no merges, no formatting, no fallbacks.*

If a page needs logic that no service exposes, the logic goes **in the service**, and the controller
gains a named forwarding function. It does not go in the controller. `engines_controller.py`'s
docstring records what happens when this slips: the panels used to hand it arbitrary callables to run
on the DB worker thread, which inverted the dependency entirely.

Two contracts must stay at zero while this phase runs — a new controller may import neither
`backend.src.db` nor a service's `repo`. The `sql` and `ui_db` structure gates must stay empty.

## The 200-line ceiling — read before writing a forwarding function

`structure_gates` enforces **two controller rules at zero, with no baseline and no allowance**:
a controller may not exceed **200 lines**, and it must be a flat `<name>_controller.py` — never a
package directory.

This phase adds forwarding functions to controllers, so it spends that budget. Current headroom:

| Controller | Lines | Headroom | Task |
|---|---|---|---|
| `sync_controller` | 166 | 34 | — |
| `history_controller` | 150 | **50** | 030 — **tightest in the phase** |
| `settings_controller` | 143 | 57 | — |
| `trading_controller` | 103 | 97 | 020 |
| `telegram_controller` | 50 | 150 | 040 |
| `ai_analysis_controller` | 30 | 170 | 030 |
| `engines_controller` | 28 | 172 | 010 |

**If a controller would cross 200, do not split it and do not create a package.** The gate rejects
both, and `controllers/remote/` + `controllers/sync/` growing to 4,950 lines inside the controller
layer is the recorded reason the rule exists. Crossing the ceiling means the *service* should expose
one coarser function — the page is asking several small questions where it should ask one.

Task 030 is where this will bite: `history_controller` has 50 lines for the analytics reads. Design
the service functions around the page's questions before writing the controller, not after.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-engine-panels.md](010-engine-panels.md) | Breakout / Reversal / Bounce panels + the mode toggle → `engines_controller` | no |
| [020-trading-and-risk.md](020-trading-and-risk.md) | Manual entry, strategy, schedule, EA templates → `trading_controller` | **YES** |
| [030-ai-and-analytics.md](030-ai-and-analytics.md) | AI provider, Claude, analytics repos, edge stats → `ai_analysis_controller` / `history_controller` | no |
| [040-notifications-and-telegram.md](040-notifications-and-telegram.md) | Email, alerts, reader, keywords → new `notifications_controller` + `telegram_controller` | no |
| [050-backtest-and-stragglers.md](050-backtest-and-stragglers.md) | New `backtest_controller`, plus whatever 010–040 left behind | no |
| [060-enforce-at-zero.md](060-enforce-at-zero.md) | Flip the contract, drop the baseline key, prove it can still fail | no |

010, 030 and 040 are independent and can run in parallel. 020 ships alone. 050 sweeps the remainder,
so it runs last before 060.

## Exit criteria

- `python -m tools.refactor_audit.import_contracts --check` reports the contract at **0**, with
  `enforced_at_zero=True` and no baseline key.
- A planted `from backend.src.services...` import in a frontend file makes the check fail — proven,
  not assumed.
- `controllers-never-import-repos`, `controllers-never-import-the-database`,
  `frontend-never-imports-the-database`, `services-never-import-controllers` all still at zero.
- `sql` and `ui_db` structure gates still empty; no file added to the `loc` baseline.
- Coverage ratchet has not fallen.
- Task 020's demo session completed and signed off.
- `python -m tools.checks all` green, output pasted into the pack's PROGRESS.md.
