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

Simon opens each file and writes on its **ANSWER:** lines — every file has the options spelled
out with examples, and *"A"* / "keep it" is a complete answer. Everything lives in this folder;
nothing technical to dig through. ([questions.md](questions.md) explains the format.)

| # | Decision | File |
|---|---|---|
| A1 | The six trading/ops defaults (order tagging, reconciliation pace, protective limits, backups, update channel, unrecognised positions) | [001-trading-defaults.md](001-trading-defaults.md) |
| A2 | Four built-but-never-connected features: keep, connect, or remove | [002-unwired-modules.md](002-unwired-modules.md) |
| A3 | News feed down: keep trading (current behaviour) or pause opens | [004-news-no-data-policy.md](004-news-no-data-policy.md) |
| A4 | Four facts only he knows (log contents, licence secret, update client, retention) | [005-fact-finding.md](005-fact-finding.md) |
| A5 | The practice-mode licence + what "handed over" means | [007-remaining-approvals.md](007-remaining-approvals.md) |

Confirming these is a *decision*. It is **not** the sign-off + demo that Part B's code changes
still require — that stays per-task below.

## Part B — Sign-off + demos (his demo terminal, after implementation)

Each row: Simon reads the task file (plain-English Problem/Decision at the top), says "build it",
the work lands test-first and green, then the **killer demo** runs on his demo terminal and he
records sign-off in [PROGRESS.md](../todo/refactor/stage3/PROGRESS.md).

| # | Change | The killer demo he watches |
|---|---|---|
| B1 | [010 order-send dedup](../todo/refactor/stage3/010-order-send-dedup.md) | Force an ack timeout → **one** position at the broker, not two |
| B2 | [020 timeout means UNKNOWN](../todo/refactor/stage3/020-timeout-means-unknown.md) | Force a 15s send timeout on a filled order → no second order, no blind retry |
| B3 | [030 broker↔DB reconciliation](../todo/refactor/stage3/030-broker-db-reconciliation.md) | Kill the app between place and record → position adopted once on restart |
| B4 | [040 no DB close on a failed broker close](../todo/refactor/stage3/040-no-db-close-on-failed-broker-close.md) | Force a close-reject → DB stays open + alert, no phantom close |
| B5 | [050 protective halts on by default](../todo/refactor/stage3/050-protective-halts-default-on.md) | Breach the daily-loss cap → new opens pause; nothing auto-closed |
| B6 | [Debug-bridge seam](../todo/refactor/infra/local-debug-mode/020-fake-mt5-bridge.md) — the 3-line `_make_bridge` branch + `run.py` bridge-skip that make `FOREX_DEBUG_MODE=1` use the already-built-and-tested fake | With debug OFF: boot connects to real MT5 exactly as today. With debug ON: offline boot, moving fake price, banner up, zero outbound connections |

B6 is the only one whose implementation already exists (the fake and its tests shipped with
stage 2); it waits purely on this sign-off. B1–B5 are specced and test-planned but not built —
they are built after Part A confirms the defaults they depend on.

## Part C — After the session

- Every Part-B row Done with sign-off + demo recorded in PROGRESS → stage 3 is clear.
- The go-live gate is [docs/simon-handover/readiness-checklist.md](readiness-checklist.md) —
  stage 3 is its last red row that matters.
- This same sitting is the natural moment to walk Simon through Start Here, the Help button,
  and debug mode — the stage-2 usability work was built for exactly this.
