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
| [010 order-send dedup](010-order-send-dedup.md) | YES | **done (2026-09-01)** — Simon's demo session; live race judged not hand-reproducible, offline coverage accepted as the answer | Simon + Claude | See "Demo 1" below. |
| [020 timeout → UNKNOWN](020-timeout-means-unknown.md) | YES | **in progress** — code + 21 tests 2026-08-29; **three further defects found and fixed 2026-08-31** (the fix never reached the primary Telegram path); awaiting demo | — | Bridge no longer retries on a lost response; new `unknown` signal status; open_from_signal routes rejections vs no-answers. Also closed the UNKNOWN case 010 had deferred. |
| [030 broker↔DB reconciliation](030-broker-db-reconciliation.md) | YES | **in progress** — diff engine + report-only pass landed 2026-08-29 | — | Pure diff engine, wired into the monitor cycle, read-only at the broker (asserted via AST). **Repairers NOT built** — they write and route through the frozen close path. |
| [040 no DB close on failed broker close](040-no-db-close-on-failed-broker-close.md) | YES | **done (2026-09-01)** — demo run and PASSED on the live demo account, both halves | Simon + Claude | See "Demo 4" below. |
| [050 protective halts on by default](050-protective-halts-default-on.md) | YES | **in progress** — demo 2026-09-01: halting and refusing PASS, "the reason names the number" FAILS (the reason is never shown to the user) | Simon + Claude | See "Demo 5" below. |
| [060 debug-bridge seam](../infra/local-debug-mode/020-fake-mt5-bridge.md) | YES | blocked (Simon) — implementation already built | — | fake + tests shipped 2026-08-11 (stage2 phase 5); only the 3-line _make_bridge branch + run.py skip await sign-off; selection pinned unchanged by tests/services/broker/test_make_bridge_debug.py |

## Decisions log
- Extracted from stage1 phase 1 into its own Simon-gated stage so stage2 is workable today (source: user, 2026-08-11)

## Verification log
- 2026-08-31 — all five demos driven end-to-end offline against the fake broker
  (`tests/e2e/test_killer_demos.py`, 10 tests: five scenarios, five negative
  controls). `tools.checks all` 8/8. **Eleven mutations, all killed** — each
  scenario was verified by re-introducing the original bug and watching it go
  red. **NO DEMO YET; no order was placed, on any account.** The owner's
  permission to use the demo account was declined per golden rule 1 and the
  runbook written instead:
  [docs/simon-handover/013-the-five-demos-runbook.md](../../../simon-handover/013-the-five-demos-runbook.md).
  **020 was found broken on the primary signal path while doing this** — see
  that task file. Nothing here is `done`.
- 2026-08-29 — 040 (partial): `tools.checks all` 8/8; 22 tests; eight mutants killed (one malformed mutation of mine produced a syntax error and was redone; one real gap found -- the alert wrapper was never exercised because the tests run under a live loop). **No demo yet.**
- 2026-08-29 — 050 (partial): `tools.checks all` 8/8; 15 tests; seven mutants all killed. Frozen close path: reporting only, close outcome asserted unaffected. **No demo yet.**
- 2026-08-29 — 030 (half): `tools.checks all` 8/8; 31 tests; eleven mutants all killed. Report-only, writes nothing. **No demo yet.**
- 2026-08-29 — 020: `tools.checks all` 8/8; twelve mutants killed (one flawed mutation of mine hit the wrong function and had to be redone; it exposed that `restore_signal_after_failed_open`'s guard had no test at all). **No demo yet.**
- 2026-08-29 — 010: `python -m tools.checks all` 8/8 green; 28 dedup tests; twelve mutants all killed (two only after strengthening my own assertions). **No demo yet — market closed.** Nothing here is `done`.

## Blockers / open
- Everything here needs Simon (sign-off + demo session).
- Money-path provisional defaults await Simon's confirmation (docs/simon-handover/001).

## Parallel-route audit, 2026-08-31

020 was found broken because its fix reached one signal route and not the
parallel one. That is a shape of failure, not a one-off, so the other four
tasks were checked the same way: **for each fix, is there a second path to the
same outcome that it does not cover?**

| Task | Paths to the outcome | Verdict |
|---|---|---|
| 010 no duplicate order | `bridge.place_order` has **one** call site in the whole tree (`open_trade.py`); the EA handoff is inside the same function | **sound** — the gate is on the funnel |
| 020 timeout → unknown | two: `open_trade_from_signal` and `scan_auto_execute` | **was broken** — see the task file; three defects, fixed |
| 030 reconciliation | one entry point, report-only | sound |
| 040 no DB close on a refused close | **four** `close_position` call sites | three were already correct (frozen path raises; ladder legs skip; residual close alerts); the fourth was `monitor_loop`, fixed on 2026-08-29 |
| 050 protective halts | the check is in `open_trade` **before** the EA handoff, so it gates both send paths | **sound** — gate on the funnel, not per caller |

The lesson worth keeping: **010 and 050 are safe because they gate a single
funnel; 020 was unsafe because it gated callers.** Where a check is repeated
per route, a route will eventually be missed.

Three properties nothing was pinning are now pinned, since all three would
break silently:

- `tests/refactor/test_order_paths_have_one_funnel.py` — `place_order` keeps
  exactly one call site, and the halt check stays above both send paths
  (4 tests, 3 mutants killed)
- `tests/trading/test_close_response_contract.py` — every branch of the real
  bridge's `_close_position` returns exactly one of `{"success": True, ...}` or
  `{"error": ...}`. The frozen close path reads `success`, so a response
  carrying neither would record a database close at the app's own local tick —
  040's exact bug, in the one function that may not be reshaped. Includes the
  non-obvious dependency that keeps it true: `_last_error` is never empty when
  the bridge is down (15 tests, 3 mutants killed)

---

## Demo 1 (task 010) — the session record, 2026-09-01

**Simon's decision:** accept the offline coverage as the answer for the race
itself, on the evidence below. Recorded by him in the session, in these words:
*"take option 3 now and 1 as the answer."*

### What was actually run

A Market Order from the Trading page, `scale_out` (non-template, EA-portable),
0.03 lots, with the EA attached and healthy, then the EA removed from the chart
as fast as possible.

```
16:34:59.736  [EA-diag] handoff check strategy=scale_out ea_instance=True ea_healthy=True portable=True
16:34:59.921  [EA] order placed: ticket=1906484660 dir=BUY lots=0.03 @ 4363.29 (strategy=scale_out)
```

**The EA acked in 185 milliseconds.** No timeout, so the Python fallback never
ran and the dedup guard was never reached. **Inconclusive, not failed** — one
position, no duplicate, nothing wrong.

### Why the race is not hand-reproducible, which is the finding

The window is between `trade.Buy()` returning and `SendJson("trade_opened")`
being sent — `mql5/ForexTraderBridge.mq5:1105` to `:1212`. Measured live at
**185ms**. No operator removes an EA inside that.

The 2026-07-30 incident had a **1 anchor + 3 pending** template against a slow
broker, where each leg is its own synchronous round trip; that is what exceeded
the timeout. But a multi-leg strategy means a template, and a template ack
timeout takes the **placeholder** branch (`if not _is_template: raise`), never
the dedup branch. So the dedup path needs *non-template AND slow EA*, and a
healthy EA cannot be made slow without editing and recompiling the EA.

Option 2 was offered — a debug-only ack delay behind a default-off flag — and
declined for now. If the race is ever wanted live, that is the route.

### What the session DID verify, and it is the part that mattered

The guard rests on two assumptions about EA behaviour that no offline test can
check, because the fake bridge is written to the same assumptions. Both were
confirmed against the real EA on a real account:

1. **The EA places the order BEFORE it acks.** Confirmed in the source at
   `:1105` (`trade.Buy`) then `:1212` (`SendJson`), and confirmed live by the
   185ms gap between the handoff check and the order-placed line.
2. **The order carries the trade id the guard searches for** —
   `"ea:" + StringSubstr(trade_id, 0, 12)`. This is the contract between the
   MQL5 EA and `_resolve_fallback_send`, in two languages with no compiler
   between them.

If either were false, the guard could not work at all, and neither is testable
offline. That is what the sitting was for.

### Two unplanned results from the same run

**The TP safety net worked on a live position.** With the EA removed mid-trade,
the trade reached TP1 unprotected and the Python loop caught it:

```
16:38:15  [TP-SafetyNet] ticket=1906484660 reached TP1 (extreme=4366.78) but was
          never protected by the live loop — SL moved to breakeven+cost 4363.64
```

Closed 16:38:19, +$9.26 realised, broker flat afterwards. Nothing stranded.

**The reconciliation report and the EA-unhealthy warning were both logging the
same line every 1-12 seconds** while two template placeholders sat out their
24-hour expiry. The reconciliation one is fixed (commit 3de72e5); the
`monitor_loop` EA-unhealthy one was found in this session and is tracked
separately.

---

## Demo 4 (task 040) — PASS, 2026-09-01

Run on the live **demo** account by Simon, watched in the log by Claude.
Manual Market Order, `scale_out`, 0.03 lots, ticket 1906600097, entry 4369.18,
`profit_close_usd` set to $1.00.

### Half one — a refused close must not become a database close

```
16:49:32.613  [ProfitClose] 131079e9-a6dd-48 hit $1.00 target
              (realised $0.00 + unrealised $1.62 = $1.62 cumulative)
16:49:32.616  [Close] trade=131079e9 ticket=1906600097 NOT closed — broker refused
              the close: Close failed retcode=10027: AutoTrading disabled by client.
              Leaving it open in the database; reconciliation will settle it.
```

`retcode=10027` is MT5's own "AutoTrading disabled by client" — a real broker
refusal, not a simulated one.

Verified in the database and at the broker rather than read off the log:

| | |
|---|---|
| Row status | `open` |
| `realised_pnl` | 0.0 |
| `close_time` / `close_price` | None |
| Closed rows for the ticket | 0 |
| Partial-close rows booked | 0 |
| Broker | still held it, +$3.24 |

Nothing booked, no phantom close, position still managed. The pre-fix
behaviour wrote a close row here and stopped managing a live position.

### Half two — and it still closes when the broker allows it

AutoTrading back on:

```
16:50:28  [ProfitClose] hit $1.00 target ($2.67 cumulative)
          POST /close/1906600097 → succeeded
```

| | |
|---|---|
| Status | `closed` |
| Close price | 4370.14 |
| `realised_pnl` | 2.88 |
| `mt5_profit` | 2.88 |
| Remaining lots | 0.0 |
| Broker | flat |

The app's figure and MT5's agree to the cent. This half matters as much as the
first: a fix that simply never closed anything would have passed half one.

### Two things observed in passing

**The idempotency guard fired on a real close.** Two close paths were in flight
at 16:50:28 (visible as a duplicate `GET /history/position/1906600097` at the
same millisecond). One booked it; the other logged
`apply_full_close ...: no open trade to close — already settled, so no balance
change and no signal update` and booked nothing. That is the double-credit
failure mode, refused on live money.

**Two concurrent close paths for one trade** is worth understanding rather
than shrugging at, even though the guard caught it and the numbers are right.
Recorded as an observation, not a defect.

**Repetition, third instance today.** Each refused attempt logged a full ERROR,
once a second, for as long as AutoTrading stayed off. Retrying is correct; a
full ERROR every second is the same problem fixed in the reconciliation pass
(commit 3de72e5) and still open in `monitor_loop`'s EA-unhealthy warning.

---

## Demo 5 (task 050) — split result, 2026-09-01

Run on the live **demo** account. Not the scripted variant: the daily-loss
limit could not be tripped (the account was **up $2.27 across 64 closed
trades**, so at 3% it needed a $46 swing). Instead the **drawdown** guard
fired on its own during demo 4, and the refusal was demonstrated against that.
Same mechanism, same code path, different threshold.

### PASS — it halts, and it refuses

```
16:50:28  [RG] Trading paused until 17:05:28:
          Total drawdown 31.6% from peak $2,140.52 (limit 10%)
17:01:04  [Pause] Trading paused until 17:05 — MT5 order blocked. (signal=e0401736)
```

The halt fired automatically on the post-close check, wrote a reason naming the
number, and blocked a subsequent order. Nothing reached the broker. Note this
also confirms the halt covers **manual** Market Orders, via the
`is_trading_paused` gate in `open_trade`.

### FAIL — "the app shows the halt reason, and the reason names the number"

The reason is written and is precise. It is never shown to the user.

Traced every reference to `risk_halt_reason` in the repository:

  * written in `services/risk/governor.py` (3 sites)
  * read in **exactly one** place: `services/signals/scan_staleness.py:204`
  * surfaced in the frontend: **nowhere at all**

What the operator sees is `Trading paused until 17:05 — MT5 order blocked.`
That gives the time and not the cause, so a drawdown halt, a daily-loss halt
and a give-back halt are indistinguishable without reading SQLite — and they
call for completely different responses.

Demonstrated today: without the reason being read out of the database by hand,
the owner would not have known which guard had stopped his account.

**Why no test caught it.** The offline tests assert the reason is written, and
it is. Whether a human ever sees it is not a property a fake can observe. This
is what the live sitting was for.

### Note for the owner, recorded because it was caused by this session

The drawdown halt fired as a direct result of two pre-flight steps: setting
`max_total_drawdown_pct` from 8 to the 10 recorded in
`simon-handover/011`, and enabling `risk_governor_enabled`. The account sits
31.6% below its peak of $2,140.52, so on any limit below ~32% it halts, and it
will re-halt after every close until the drawdown or the peak changes. Raising
the limit, re-baselining the peak, or leaving it halted is the owner's
decision and nothing has been changed.
