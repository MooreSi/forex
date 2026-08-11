# Stage 3 (money path) — PROGRESS

**Shared status log. Every task here is money-touching and blocked on Simon** (sign-off + demo
session). A green suite is necessary but NOT sufficient — Notes must record Simon's sign-off + the
demo session before any task is `done`.

_Last updated: 2026-08-11 — extracted from stage1 phase 1; no code started._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit + **Simon sign-off + demo**)

## Overall
- All tasks blocked on Simon (sign-off + demo). Confirm the money-path defaults
  ([../../questions/001-trading-defaults.md](../../../questions/001-trading-defaults.md)) first.

## Tasks

| Task | Money | Status | Owner | Notes |
|---|---|---|---|---|
| [010 order-send dedup](010-order-send-dedup.md) | YES | blocked (Simon) | — | SPEC-002 C1; trade id at broker + pre-send check |
| [020 timeout → UNKNOWN](020-timeout-means-unknown.md) | YES | blocked (Simon) | — | timeout/None/exception = UNKNOWN, never re-fired |
| [030 broker↔DB reconciliation](030-broker-db-reconciliation.md) | YES | blocked (Simon) | — | startup + periodic; broker is source of truth |
| [040 no DB close on failed broker close](040-no-db-close-on-failed-broker-close.md) | YES | blocked (Simon) | — | route through frozen wrappers |
| [050 protective halts on by default](050-protective-halts-default-on.md) | YES | blocked (Simon) | — | daily-loss/drawdown/breaker armed; un-swallow recording |

## Decisions log
- Extracted from stage1 phase 1 into its own Simon-gated stage so stage2 is workable today (source: user, 2026-08-11)

## Verification log
- (none yet — blocked on Simon)

## Blockers / open
- Everything here needs Simon (sign-off + demo session).
- Money-path provisional defaults await Simon's confirmation (docs/questions/001).
