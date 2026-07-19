# Breakout Signal Migration — PROGRESS

_Last updated: 2026-07-19 — ALL of 010-040 done. Pack complete._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [characterize-breakout-current-behavior](010-characterize-breakout-current-behavior.md) | done | agent, 2026-07-19 | 42 tests, all green against current code. **Found a real, live bug**: breakout_signal's virtual balance double-counts partial-close profits on final close (see task file). Reported to Simon via Telegram. |
| 020 | [migrate-breakout-repo-layer](020-migrate-breakout-repo-layer.md) | done | agent, 2026-07-19 | `breakout_signal_repo.py` on the shared adapter; `close_signal`/`book_partial_close`/`update_signal_pnl_from_mt5` now atomic. 3 new named functions added (`get_last_signal_time_for_level`, `get_recent_outcomes_by_direction`, `set_stop_loss`) replacing raw-SQL bypasses. **Double-counting bug preserved faithfully, not fixed** — atomicity and correctness are separate concerns. 88 tests, all green. |
| 030 | [extract-breakout-service-layer](030-extract-breakout-service-layer.md) | done | agent, 2026-07-19 | `engine.py` split into `breakout_signal_service.py` (764 lines, close to the 800 ceiling) + 4 mixin files. 94 tests, all green. Caught and fixed a real bug before commit: 2 of the new files initially imported the wrong (old) DB module. 2 more raw-SQL bypasses found and fixed. 7 external call sites confirmed, `engine.py`/`database.py` left in place. |
| 040 | [mt5-connectivity-check](040-mt5-connectivity-check.md) | done | agent, 2026-07-19 | Isolated terminal reused, confirmed connectivity + real M5/H1/H4 candle data across all 3 timeframes. Live terminal untouched. Closed after. |

## Decisions log
- Same pattern as backend-foundation/gd_copy_signal, reusing the shared DB adapter (source: user, 2026-07-19, "continue with the refactoring")

## Blockers / open
None. Pack complete.

**Carried forward for whichever pack comes next** (not blockers on this pack):
1. Wire `breakout_signal_service.py`/`breakout_signal_repo.py` into the 7 external call sites
   (`ui/app.py`, `ui/pages/remote_node.py`, `ui/pages/breakout_panel.py`,
   `core/app_lifecycle.py`, `breakout_signal/ml_engine.py`, `breakout_signal/adaptive_params.py`,
   `sync/server.py`) and retire the old `engine.py`/`database.py`.
2. **Simon's live-app decision still pending** (asked via Telegram, 2026-07-19): fix the
   Breakout Engine's balance double-counting bug directly on the live app now, or leave it for
   when the refactor eventually replaces this engine.
3. `breakout_signal_service.py` at 764 lines is close to the 800 ceiling (not "well under" like
   gd_copy_signal's files) — worth a further split if this engine is revisited.
