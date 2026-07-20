# Core ORB Fixed Handler Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-handle-orb-fixed | done | agent, 2026-07-20 | 5 tests, all green against unmodified `engine.py`. No bugs found. |
| 020 | extract-handle-orb-fixed | done | agent, 2026-07-20 | Created `core_handle_orb_fixed.py` (67 lines, 1:1 port). 5 new surface tests. 484/484 green in tests/core/. `engine.py` untouched. No real/demo order ever placed/closed/modified. |

## Blockers / open
None. Pack complete — first pack of the TP/SL strategy-handler cluster. 12 handlers remain,
each needing its own scoping pass given the wide size/complexity variance surveyed in the
README (most are 100-200+ lines with retry-cooldown instance state and multiple bridge calls).
