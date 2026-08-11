# The Simon session — agenda for the sign-off + demo sitting

**Who:** Simon (decides) + Darren (drives) · **Where:** Simon's machine, his MT5 demo terminal
**What this is:** the one sitting that clears everything currently blocked on Simon. Nothing on
this page places a live order — every demo runs on his demo account, and tests never touch a
broker at all.

Estimated shape: ~30 minutes of decisions (Part A), then the implementation work happens
(Darren/agent, after the decisions), then a second sitting for the demos (Part B). Parts A and B
do not need to be the same day.

---

## Part A — Decisions (30 min, no code involved)

Simon reads each item and writes his answer inline. "Confirm the provisional" is a complete
answer everywhere.

| # | Decision | Where to answer |
|---|---|---|
| A1 | The six trading/ops defaults (order-id transport, reconciliation mode, halt thresholds, backups, update channel, manual positions) | [docs/questions/001-trading-defaults.md](../../questions/001-trading-defaults.md) |
| A2 | Four built-but-unwired modules: wire or remove? (2 of 4 are his: licence client, TEST-module auth) | [docs/questions/002-unwired-modules.md](../../questions/002-unwired-modules.md) |
| A3 | News data missing/stale: trade through (current behaviour) or pause opens? | [docs/questions/004-news-no-data-policy.md](../../questions/004-news-no-data-policy.md) |
| A4 | Operator facts only he knows (live-log contents, licence-secret rotation, update client, retention) | [docs/questions/005-fact-finding.md](../../questions/005-fact-finding.md) |
| A5 | Debug licence policy: bless that the repo's key generator can self-licence for local dev (already implemented, 30-day expiry, `guard.enforce()` untouched) | [local-debug-mode QUESTIONS #1](../infra/local-debug-mode/QUESTIONS.md) |
| A6 | The "giveable" bar: demo-session handoff (recommended) vs full self-serve | [stage2 QUESTIONS #5](../stage2/QUESTIONS.md) |

Confirming these is a *decision*. It is **not** the sign-off + demo that Part B's code changes
still require — that stays per-task below.

## Part B — Sign-off + demos (his demo terminal, after implementation)

Each row: Simon reads the task file (plain-English Problem/Decision at the top), says "build it",
the work lands test-first and green, then the **killer demo** runs on his demo terminal and he
records sign-off in [PROGRESS.md](PROGRESS.md).

| # | Change | The killer demo he watches |
|---|---|---|
| B1 | [010 order-send dedup](010-order-send-dedup.md) | Force an ack timeout → **one** position at the broker, not two |
| B2 | [020 timeout means UNKNOWN](020-timeout-means-unknown.md) | Force a 15s send timeout on a filled order → no second order, no blind retry |
| B3 | [030 broker↔DB reconciliation](030-broker-db-reconciliation.md) | Kill the app between place and record → position adopted once on restart |
| B4 | [040 no DB close on a failed broker close](040-no-db-close-on-failed-broker-close.md) | Force a close-reject → DB stays open + alert, no phantom close |
| B5 | [050 protective halts on by default](050-protective-halts-default-on.md) | Breach the daily-loss cap → new opens pause; nothing auto-closed |
| B6 | [Debug-bridge seam](../infra/local-debug-mode/020-fake-mt5-bridge.md) — the 3-line `_make_bridge` branch + `run.py` bridge-skip that make `FOREX_DEBUG_MODE=1` use the already-built-and-tested fake | With debug OFF: boot connects to real MT5 exactly as today. With debug ON: offline boot, moving fake price, banner up, zero outbound connections |

B6 is the only one whose implementation already exists (the fake and its tests shipped with
stage 2); it waits purely on this sign-off. B1–B5 are specced and test-planned but not built —
they are built after Part A confirms the defaults they depend on.

## Part C — After the session

- Every Part-B row Done with sign-off + demo recorded in PROGRESS → stage 3 is clear.
- The go-live gate is [docs/give-to-simon-checklist.md](../../give-to-simon-checklist.md) —
  stage 3 is its last red row that matters.
- This same sitting is the natural moment to walk Simon through Start Here, the Help button,
  and debug mode — the stage-2 usability work was built for exactly this.
