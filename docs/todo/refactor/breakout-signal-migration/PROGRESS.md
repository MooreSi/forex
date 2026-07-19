# Breakout Signal Migration — PROGRESS

_Last updated: 2026-07-19 — pack scaffolded, starting 010._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [characterize-breakout-current-behavior](010-characterize-breakout-current-behavior.md) | done | agent, 2026-07-19 | 42 tests, all green against current code. **Found a real, live bug**: breakout_signal's virtual balance double-counts partial-close profits on final close (see task file). Reported to Simon via Telegram. |
| 020 | [migrate-breakout-repo-layer](020-migrate-breakout-repo-layer.md) | done | agent, 2026-07-19 | `breakout_signal_repo.py` on the shared adapter; `close_signal`/`book_partial_close`/`update_signal_pnl_from_mt5` now atomic. 3 new named functions added (`get_last_signal_time_for_level`, `get_recent_outcomes_by_direction`, `set_stop_loss`) replacing raw-SQL bypasses. **Double-counting bug preserved faithfully, not fixed** — atomicity and correctness are separate concerns. 88 tests, all green. |
| 030 | [extract-breakout-service-layer](030-extract-breakout-service-layer.md) | done | agent, 2026-07-19 | `engine.py` split into `breakout_signal_service.py` (764 lines, close to the 800 ceiling) + 4 mixin files. 94 tests, all green. Caught and fixed a real bug before commit: 2 of the new files initially imported the wrong (old) DB module. 2 more raw-SQL bypasses found and fixed. 7 external call sites confirmed, `engine.py`/`database.py` left in place. |
| 040 | [mt5-connectivity-check](040-mt5-connectivity-check.md) | not started | — | Depends on 030 (done) — ready to start |

## Decisions log
- Same pattern as backend-foundation/gd_copy_signal, reusing the shared DB adapter (source: user, 2026-07-19, "continue with the refactoring")

## Blockers / open
None.
