# Stage 3 (money path) — PROGRESS

**Shared status log. Every task here is money-touching and blocked on Simon** (sign-off + demo
session). A green suite is necessary but NOT sufficient — Notes must record Simon's sign-off + the
demo session before any task is `done`.

_Last updated: 2026-08-11 — pack is READY FOR SIMON: the agenda is
[docs/simon-handover/session-agenda.md](../../../simon-handover/session-agenda.md); 060 (debug
seam) added so everything Simon-gated lives in one view. No money code started._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit + **Simon sign-off + demo**)

## Overall
- All tasks blocked on Simon (sign-off + demo). Confirm the money-path defaults
  ([../../simon-handover/001-trading-defaults.md](../../../simon-handover/001-trading-defaults.md)) first.

## Tasks

| Task | Money | Status | Owner | Notes |
|---|---|---|---|---|
| [010 order-send dedup](010-order-send-dedup.md) | YES | **in progress** — code + 28 tests landed 2026-08-29, awaiting demo | — | Gate built and mutation-tested; killer demo (pause the EA, force an ack timeout) needs a live EA, market closed until Monday. UNKNOWN-state handling deferred to 020 on purpose. |
| [020 timeout → UNKNOWN](020-timeout-means-unknown.md) | YES | **in progress** — code + 21 tests landed 2026-08-29, awaiting demo | — | Bridge no longer retries on a lost response; new `unknown` signal status; open_from_signal routes rejections vs no-answers. Also closed the UNKNOWN case 010 had deferred. |
| [030 broker↔DB reconciliation](030-broker-db-reconciliation.md) | YES | **in progress** — diff engine + report-only pass landed 2026-08-29 | — | Pure diff engine, wired into the monitor cycle, read-only at the broker (asserted via AST). **Repairers NOT built** — they write and route through the frozen close path. |
| [040 no DB close on failed broker close](040-no-db-close-on-failed-broker-close.md) | YES | blocked (Simon) | — | route through frozen wrappers |
| [050 protective halts on by default](050-protective-halts-default-on.md) | YES | blocked (Simon) | — | daily-loss/drawdown/breaker armed; un-swallow recording |
| [060 debug-bridge seam](../infra/local-debug-mode/020-fake-mt5-bridge.md) | YES | blocked (Simon) — implementation already built | — | fake + tests shipped 2026-08-11 (stage2 phase 5); only the 3-line _make_bridge branch + run.py skip await sign-off; selection pinned unchanged by tests/services/broker/test_make_bridge_debug.py |

## Decisions log
- Extracted from stage1 phase 1 into its own Simon-gated stage so stage2 is workable today (source: user, 2026-08-11)

## Verification log
- 2026-08-29 — 030 (half): `tools.checks all` 8/8; 31 tests; eleven mutants all killed. Report-only, writes nothing. **No demo yet.**
- 2026-08-29 — 020: `tools.checks all` 8/8; twelve mutants killed (one flawed mutation of mine hit the wrong function and had to be redone; it exposed that `restore_signal_after_failed_open`'s guard had no test at all). **No demo yet.**
- 2026-08-29 — 010: `python -m tools.checks all` 8/8 green; 28 dedup tests; twelve mutants all killed (two only after strengthening my own assertions). **No demo yet — market closed.** Nothing here is `done`.

## Blockers / open
- Everything here needs Simon (sign-off + demo session).
- Money-path provisional defaults await Simon's confirmation (docs/simon-handover/001).
