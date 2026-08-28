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

## Part B2 — The 2026-08-25 merge's money-path changes (added 2026-08-28)

Everything below is **written, tested and green**, and **none of it has been near a
broker**. It is not stage-3 work; it arrived with the upstream merge or was found
while draining that code, and it needs the same demo treatment for the same reason.

Two are live bug fixes with observed cost. The rest are relocations where the tests
say behaviour is unchanged and only a demo can confirm the tests were asking the
right question.

| # | Change | The demo he watches |
|---|---|---|
| M1 ✅ | **VERIFIED on demo 2026-08-28.** ticket 1883252429, SELL 0.1 @ 4577.88 on `template:Harvest $30`, closed 27s later at 4574.97 for **+$29.10** -- the template's own $30, not the global $75. Closing deal comment empty = EA `PositionClose()`, not a stop or target. All 22 templates read `harvest_pips=0.0` and the EA received it. **Harvest threshold fix** — `harvest_pips` (pips) was being read as `harvest_threshold` (account currency), and shipped defaulting to `1.0` rather than off. Two live trades closed at ~C$1.40 against a $30 setting. Migration 29 clears the stale `1.0`. | Set a harvest threshold of $30 on a demo template, open a position, let it run past +$1.40. **It must NOT close.** Then confirm the basket closes when the account-currency figure genuinely reaches $30. |
| M2 | **IME toggle fix** — the Telegram panel's Immediate Market Entry button could turn IME on but never off; the two reads used different config keys, so the "off" write landed where the "on" read never looked. | Toggle IME **off** on a channel, send a signal whose price has already left the zone. **No market order.** Toggle on, repeat, confirm it fires. Re-open the panel between steps -- the original bug only showed on re-read. |
| M3 | **~20 money-path files had their SQL moved into repos** (pending activation, ea_bridge, scan_auto_execute, open_from_signal, instant_followup, template placeholder repair, orphan reconcile, second-message merge). Statements moved verbatim; each is covered by a test written first and confirmed by mutation. | One full signal -> open -> manage -> close cycle on demo, then check the DB row against the terminal: entry, lots, SL/TP, and the closed P&L match. This is the broad "did the drain change anything" check. |
| M4 | **Anti-compounding revert** in the pending-signal watcher. Its absence previously walked one signal's stop 110 pips over 80 passes. Now tested, never demo'd. | Queue a signal outside its zone with IME on, force the activation to fail (schedule gate is easiest). Watch the stored levels: they must return to what the channel sent, and stay there across repeated passes. |
| M5 | **Fixed R:R post-fill SL/TP override** — corrects both levels from the actual fill and pushes them to the broker. Newly tested this session; the rejection arm has a live incident behind it. | Open a Fixed R:R trade on demo. Confirm MT5 holds **both** a stop and a target, and that both match the app's row. If the broker ever refuses the sync, the log must say REJECTED and the trade must still be tracked. |
| M6 | **EA template + global-config pushes now route through a controller** (`push_template`, `push_global_config`). Same calls, no longer holding the live bridge object. | Send a template to a connected EA from the Trading page, and save Global Parameters. Both must reach the EA exactly as before. With the EA disconnected, both must warn rather than error. |
| M7 | **Two runtime loops relocated** into their services (auto-template regime picking, signal snapshot). | Leave the app running an hour on demo with an Auto channel configured. The regime baseline should still be applied, the AI review should fire at most ~4/hour, and the snapshot log should keep filling. |

**Order matters.** M1 and M2 are fixes to observed live losses -- do those first and
alone, so a surprise is unambiguous. M3 is the broad regression check. M4-M7 can share
a session.

**If any of these is wrong, it is wrong with real money.** None is a "probably fine".

## Part C — After the session

**The bar Simon set (Q007 #2).** "Handed over" means full self-serve: he can
install, configure and run the app alone from the docs. Part B's demos are still
required on top — no answer here can waive watching the money-path changes run.
So Part C now has a documentation deliverable as well as the demo sign-offs.


- Every Part-B row Done with sign-off + demo recorded in PROGRESS → stage 3 is clear.
- The go-live gate is [docs/simon-handover/readiness-checklist.md](readiness-checklist.md) —
  stage 3 is its last red row that matters.
- This same sitting is the natural moment to walk Simon through Start Here, the Help button,
  and debug mode — the stage-2 usability work was built for exactly this.
