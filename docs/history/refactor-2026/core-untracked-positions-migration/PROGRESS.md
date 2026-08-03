# Core Untracked MT5 Positions Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-untracked-positions | done | agent, 2026-07-20 | 5 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-untracked-positions | done | agent, 2026-07-20 | Created `core_untracked_positions.py` (36 lines, 1:1 port; `bridge` taken explicitly, calls pack 3's `get_open_trades()` directly). 5 new surface tests. 210/210 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete — closes pack 3's deferral. `engine.py` still calls its own original inline
logic; wiring the new module in (or choosing the next `core/engine.py` domain pack) is future
work, not yet scoped.
