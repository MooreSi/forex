# Core Signal CRUD Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-signal-crud | done | agent, 2026-07-20 | 12 tests, all green against unmodified `engine.py`. No bugs found — every method was already a single `db_module.db()` block. |
| 020 | extract-signal-crud | done | agent, 2026-07-20 | Created `core_signals.py` (91 lines, 1:1 port, no logic changes). 12 new surface tests, 010's assertions re-pointed at the new functions. 106/106 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete — `engine.py` still calls its own original inline logic; wiring the new
module in (or choosing the next `core/engine.py` domain pack) is future work, not yet scoped.
