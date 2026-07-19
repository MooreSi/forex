# Breakout Signal Migration — PROGRESS

_Last updated: 2026-07-19 — pack scaffolded, starting 010._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [characterize-breakout-current-behavior](010-characterize-breakout-current-behavior.md) | done | agent, 2026-07-19 | 42 tests, all green against current code. **Found a real, live bug**: breakout_signal's virtual balance double-counts partial-close profits on final close (see task file). Reported to Simon via Telegram. |
| 020 | [migrate-breakout-repo-layer](020-migrate-breakout-repo-layer.md) | not started | — | Depends on 010 (done) — ready to start |
| 030 | [extract-breakout-service-layer](030-extract-breakout-service-layer.md) | not started | — | Depends on 020 |
| 040 | [mt5-connectivity-check](040-mt5-connectivity-check.md) | not started | — | Depends on 030 |

## Decisions log
- Same pattern as backend-foundation/gd_copy_signal, reusing the shared DB adapter (source: user, 2026-07-19, "continue with the refactoring")

## Blockers / open
None.
