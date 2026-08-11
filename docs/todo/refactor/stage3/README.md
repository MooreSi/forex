# Stage 3 — Simon-gated work (the money path)

**Status:** ready for Simon — not started, but everything he needs to run the session is prepared:
**[SIMON-SESSION.md](SIMON-SESSION.md)** is the agenda (decisions first, then per-task sign-off +
demo on his machine)
**Touches money:** YES — every task here changes order placement, closing, sizing or the halts.
**Created:** 2026-08-11 (extracted from stage1 phase 1 so stage2 is workable today)

## Why this is its own stage

Stages 1 and 2 are work an agent can do now. **Stage 3 is everything that needs Simon** — he holds
the live account, makes the money decisions, and the golden rules require his sign-off plus a demo
session watching real trades before any of this ships. Keeping it separate means the rest of the
roadmap never stalls waiting on him.

## 👋 Picking this up

1. Read [../HANDOFF.md](../HANDOFF.md) and the golden rules. Run `/safe-change` before
   touching any task here.
2. **Do not ship any of this without Simon** — sign-off + demo session, both recorded in PROGRESS.
3. Confirm the money-path provisional defaults first: [../../questions/001-trading-defaults.md](../../../questions/001-trading-defaults.md)
   (Simon confirms the six defaults adopted provisionally on 2026-08-10).
4. Tests use fakes/sentinels only — **no real or demo order in any test**.

## The problem (why these exist)

From the 2026-08-08 risk + backend reviews: one signal can fire **two** live orders through three
timeout/retry gaps; a broker action and its DB record aren't atomic and nothing reconciles them; a
failed broker close can be recorded as done; and the protective halts default OFF. These are the
reasons the app is not yet safe to run live.

## Tasks (run in order; each is `/safe-change` + Simon)

| Task | What | Killer demo (on Simon's terminal) |
|---|---|---|
| [010 order-send dedup](010-order-send-dedup.md) | A trade id at the broker + a pre-send check, so a retry/fallback can't double-fire | Force an EA-ack timeout → **one** live position, not two |
| [020 timeout → UNKNOWN](020-timeout-means-unknown.md) | A timeout/None/exception on send is UNKNOWN, never "didn't happen" — never re-pended/retried blindly | Force a 15s send timeout on a filled order → no second order, no re-open |
| [030 broker↔DB reconciliation](030-broker-db-reconciliation.md) | Startup + periodic reconcile; broker is the source of truth for what exists | Kill the app between place and DB-record → the position is adopted once, not orphaned or duplicated |
| [040 no DB close on a failed broker close](040-no-db-close-on-failed-broker-close.md) | Never record a DB close when the broker close failed/raised (route through the frozen wrappers) | Force a broker close-reject → DB stays open + an alert, not a phantom close |
| [050 protective halts on by default](050-protective-halts-default-on.md) | Daily-loss / drawdown / circuit-breaker armed by default; un-swallow the breaker recording | Breach the daily-loss cap → new opens pause (nothing auto-closed) |
| [060 debug-bridge seam](../infra/local-debug-mode/020-fake-mt5-bridge.md) | The 3-line `_make_bridge` debug branch + `run.py` bridge-skip. The fake + its tests already shipped (stage2 phase 5) — only this wiring waits on Simon | Debug OFF: boots against real MT5 exactly as today. Debug ON: offline boot, moving fake price, banner, zero outbound connections |

## Anchor specs

The money-path design was anchored on SPEC-002 (order-send idempotency) and SPEC-003 (broker↔DB
reconciliation). Those spec files were lost in a docs reorganisation; their substance lives in the
task files above. Re-materialise the formal Problem/Non-goals/Test-plan documents if Simon wants
them before the demo session.

## What must NOT change

- The frozen close path (`close_trade`, `record_close`, `_make_close_trade_ctx`,
  `partial_close_trade`) — called by these tasks, never reshaped. Its characterization test passes
  unmodified.
- Order/close/sizing behaviour changes ONLY as each task deliberately specifies, under Simon's
  sign-off. No ratchet baseline rises; `python -m tools.checks all` green throughout.

## Exit criteria (the gate for "safe to run live")

Every task Done, each with Simon's sign-off + demo recorded in PROGRESS, and its killer demo passing
on his terminal. Then stage3 is clear and the app is safe for Simon to run live.
