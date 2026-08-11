# Trading-Safety and Financial-Risk Review — 2026-08-11

Read-only re-review of the money path at `c:\dev\forex\app`, three days after the
2026-08-08 review. No code was run, no MT5 contact was made. Verification method:
every previous P0/P1 claim was re-checked against the current source, and
`git diff --stat 60ccddb..HEAD` was used to confirm which files changed at all.

## Summary

**Verdict: every money-path Critical and High from 2026-08-08 is still in the code,
unchanged.** The diff since `60ccddb` touches config, auth, migrations, fakes, AI/news/email
stubs and dead-code deletion — not one line of `open_trade.py`, `close_trade.py`,
`monitor_loop.py`, `mt5_client.py`, `mt5_bridge.py`, `position_sync.py`, `governor.py`,
`trade_repo.py` or `ForexTraderBridge.mq5` changed. This matches what the remediation
pack itself says (`docs/todo/refactor/stage1/PROGRESS.md:31` — the money tasks were
"moved to stage 3, Simon-gated" on 2026-08-11), so the docs are honest; but anyone
reading "remediation pack landed" and assuming the P0s are fixed would be wrong.
The refactor work that did land (gates fail closed, migrations fail closed, daily DB
backups, localhost bind, news-calendar off the event loop) is genuinely good and
genuinely off the money path. One **new Critical** was introduced by the half-shipped
debug mode: a `FOREX_DEBUG_MODE=1` boot swaps in the fake Telegram reader and paints a
banner saying "no real orders", but the bridge seam was **not** swapped — on a Windows
machine with MT5 and `bridge_credentials.json` present, a debug boot logs into the
real account and every order path fires real orders under a banner asserting the
opposite.

## Previous findings: verification

| Finding | Status | Evidence (current code) |
|---|---|---|
| **P0-1 / C1** — EA ack timeout falls back to Python bridge → double-fire | **NOT FIXED** | `backend/src/services/broker/ea_bridge.py:170,253` (5 s ack wait); `backend/src/services/trading/open_trade.py:321-324` (`except Exception` on the handoff logs "falling back to Python bridge") → `open_trade.py:334` re-sends via `bridge.place_order`. EA side still has no trade_id dedup: `mql5/ForexTraderBridge.mq5:411-465` (`HandleOpenTrade`) never calls `FindManagedByTradeId` (defined at `:319`) before `trade.Buy/Sell` at `:459/:464`. |
| **P0-1 / C2** — send timeout re-arms the signal to `pending` (re-openable) | **NOT FIXED** | `backend/src/services/broker/mt5_client.py:292` (15 s timeout), `:304-305` (any exception → `{"error": ...}`); `open_trade.py:339-341` raises; `open_from_signal.py:95-98` → `trade_repo.restore_signal_after_failed_open` (`trade_repo.py:360-366`) unconditionally puts the signal back to `pending`. No idempotency key on the order, no broker-state check before restore. |
| **P0-1 / C3** — bridge fill-mode loop re-sends after `order_send` returns `None` | **NOT FIXED** | `mt5_bridge.py:711-716`: `result = mt5.order_send(request); if result is None: continue` — a no-response (unknown outcome) is retried as if it were a rejection, in all three fill-mode iterations. |
| **P0-2** — timeout/None/exception = UNKNOWN + reconciliation layer | **NOT FIXED** | No new reconciliation code exists anywhere under `backend/src/services/broker/` (dir listing: same modules as 2026-08-08 plus `fake_bridge.py`/`fake_market.py`, which are test/debug fakes). `mt5_client.get_positions` still returns `[]` on any exception (`mt5_client.py:273-282`); `place_order`/`close_position` still collapse timeout → `{"error"}` (`:286-319`). |
| **P0-3 / H1** — profit-close records DB close even when broker close failed | **NOT FIXED** | `backend/src/services/positions/monitor_loop.py:121-127`: `bridge.close_position` errors only `log.warning`-ed; non-success ignored; `record_close` runs unconditionally at `:128`. Contrast the frozen path, which raises (`close_trade.py:113-121`). |
| **P0-6** — protective halts on by default | **NOT FIXED** | `backend/migrations/registry.py:133` (`risk_governor_enabled INTEGER NOT NULL DEFAULT 0`) and `:142` (`circuit_breaker_enabled ... DEFAULT 0`). Enforcement still gated: `close_trade.py:231`, `circuit_breaker_repo.py:41,62`. The breaker-recording swallow is also still there: `close_trade.py:262-263` (`except ... log.debug`). |
| **P1-3** — `max_open_trades` atomicity | **NOT FIXED** | `open_trade.py:203-206`: count-then-act; the awaits at `:212` (tick), `:300` (EA ack) and `:334` (place_order) all sit between the check and the insert at `:349`. Same guardless count in `instant_entry.py:158-163`. |
| **P1-4 / H3** — `record_close` idempotency/status guard | **NOT FIXED** | `close_trade.py:136-152`: no status check before `apply_full_close`; `trade_repo.py:180-200`: the UPDATE has `WHERE trade_id=?` only — no `AND status='open'` claim, and the balance update at `:193-196` applies on every call, so a double close still double-counts P&L. The EA-managed race window is unchanged: `monitor_cycle.py:144-155` runs `reconcile_sl_hit`/profit-close **before** the `managed_by == "ea"` skip at `:164-166`. |
| **H2** — profit-close / SL-reconcile bypass ladder handling | **NOT FIXED** | `monitor_loop.py:119-128` and `:90-94` still close/record against the anchor ticket only; `close_trade.py:96-99` remains the only ladder-aware full close. |
| **H4** — one ambiguous empty `get_positions()` → local close, no miss-streak | **NOT FIXED** | `monitor_loop.py:56-90`: exception path at `:87-88` logs and falls through to `record_close` at `:90`. (`position_sync.py:108-112` does check bridge health; `reconcile_sl_hit` still doesn't.) |
| **H5** — close/partial-close IOC-only, no fill-mode fallback; pre-trade tick as close price | **NOT FIXED** | `mt5_bridge.py:799` and `:839` still hardcode `ORDER_FILLING_IOC`; `_close_position` still returns the pre-trade `tick.bid/ask` as `close_price` (`:787,:803`) instead of `result.price`. Opens retry RETURN/IOC/FOK (`:689-692`); closes do not. |
| **H6** — untracked importer auto-adopts any broker position | **NOT FIXED** | `position_sync.py:245-268`: any unknown ticket is imported with the default strategy and actively managed. |
| **H7** — sizing balance falls back to drifted sim ledger | **NOT FIXED** | `close_trade.py:74-84` (`get_trading_balance` → `vantage_simulation_account` fallback), used for sizing in `manual_market_order.py:123` and `instant_entry.py:189,227`. |
| **M2** — min-lot floor overrides risk ceiling in `suggest_lot_size` | **NOT FIXED** | `fees_sizing.py:86`: `lot = max(min_lot, min(lot, round(risk_capped_lot, 2)))`. Same floor pattern in `instant_entry.py:230` and `manual_market_order.py:125` (`max(0.01, ...)`). RG path still correctly rejects (`governor.py:183-187`). |
| **M3** — directional cap hardcoded `>= 2` in RG sizer | **NOT FIXED** | `governor.py:208-213` literal 2 vs the `max_unprotected_trades` tunable read at `:136-138`. |
| **M4/M5** — check-then-act gate; UTC+3 hardcoded | **NOT FIXED** | `open_trade.py:203-206`; `governor.py:148-152`. |
| P0-4 — dashboard bound to localhost | **FIXED** (adjacent scope, verified) | `backend/src/config/__init__.py:177-182`: default host `127.0.0.1`, non-loopback warning per PROGRESS.md 1/050. |

## New findings

### Critical

**C-NEW-1. Debug mode is half-wired: fake inputs, REAL broker output, under a banner
that says "no real orders".**
`backend/src/app.py:40-44` swaps in `FakeTelegramReader` when `config.get("debug_mode")`,
and `frontend/components/debug_banner.py:17-20` renders *"DEBUG MODE — simulated data,
no real orders. Prices, signals and AI text are fakes."* But the bridge seam was not
swapped: `backend/src/runtime.py:170-179` (`_make_bridge`) has **no debug branch** — on
Windows with the MetaTrader5 package importable it returns `NativeMT5Bridge()`
unconditionally (`:176-178`). `FakeMT5Bridge` exists but its own docstring admits it
is "NOT wired into the runtime" (`backend/src/services/broker/fake_bridge.py:21-23`).
`NativeMT5Bridge.startup` execs `mt5_bridge.py` in-process (`mt5_native.py:68-80`),
which reads `bridge_credentials.json` / `MT5_LOGIN` env (`mt5_bridge.py:118-128`) and
logs into the real account (`:146,:164`). Debug DB isolation
(`config/__init__.py:202-205`) isolates only the *database file* — not the broker,
not the credentials file.
**Failure scenario:** Simon or Darren boots with `FOREX_DEBUG_MODE=1` on the machine
that has MT5 + credentials, trusts the amber banner, and clicks the Market Order
button (or enables auto-exec so the scripted `tp1-hit.json` fake signals flow through
the real pipeline — `fake_reader.py:1-14` deliberately feeds the *real* parser and
execution path). `open_manual_market_order` → `open_trade` → `NativeMT5Bridge.place_order`
fires a **real live order**. Worse, the fresh debug DB has all halts at their
default-OFF values and no trade history, so every protective layer is at its weakest
exactly when the operator believes nothing is real. Until the `_make_bridge` seam
lands, debug mode should refuse to construct a real bridge (or at minimum the banner
must not claim "no real orders").

### High

**H-NEW-1. The remediation narrative is ahead of the code for anyone not reading the
fine print.** Not a code bug, but a live money-relevant process risk: the stage1 pack
title is "stop the bleeding", the overall status reads "'Trustworthy to run locally'
bar essentially met" (`docs/todo/refactor/stage1/PROGRESS.md:21`), and 18 commits of
visible activity landed — while **zero** of the six order-send/close/halt Criticals
changed. The handover pack for Simon (`docs/simon-handover/`, commit `4f85e1a`) is the
place this must be unmissable: if Simon reads "phase 1: stop the bleeding" plus a green
CI badge and enables live trading, C1/C2/C3/H1 are all still armed. Recommend the
2026-08-11 synthesis state, in the first paragraph Simon sees: *no money-path fix has
landed; the three double-fire windows and the close-vs-DB divergence are live.*

### Medium

**M-NEW-1. `apply_full_close` unconditionally credits the sim-account balance on every
call** (`trade_repo.py:193-196`) — this is the concrete double-count mechanism behind
P1-4: two racing closers each add `net_delta` to `vantage_simulation_account`, which is
also the sizing fallback (H7) and the ledger already documented as $707 vs $1122 drifted
(`governor.py:222-225`). Each duplicate close compounds the drift in the number that
sizes trades when the bridge blips. A `WHERE status='open'` on the trade UPDATE plus
skipping the balance write when `rowcount == 0` closes both holes in one statement.

**M-NEW-2. Debug dashboard login is a hardcoded credential pair in source**
(`backend/src/services/auth/dashboard_auth.py:48`, `_DEBUG_USERNAME`/`_DEBUG_PASSWORD`).
On its own this is Low (localhost-only, debug-only), but combined with C-NEW-1 the
"debug" login can front a UI that places real orders. Fixing C-NEW-1 demotes this to
hygiene.

### Low

**L-NEW-1. `instant_entry` non-governor sizing floors to 0.01 lots** (`instant_entry.py:230`)
— same divergence class as M2: the RG branch rejects (`:196-199`), the fallback branch
floors. One more copy of the pattern to fix when M2 is fixed.

**L-NEW-2. The `[EA-diag]` TEMP log from 2026-07-17 is still in place**
(`open_trade.py:245-253`) — the EA-handoff misbehaviour it was added to diagnose is
apparently still undiagnosed. Worth answering before ever re-enabling
`ea_bridge_enabled`, since C1 lives on exactly that path.

## Refactor quality — honest assessment

**Genuinely improved (real, verified, off the money path):**
- Guardrails now fail closed: the vacuous orphan gate was replaced with a
  module-reachability gate, coverage is actually fed, and CI runs `tools.checks all`
  on push (commits `3a2edef`, PROGRESS 2/010). Green now means something.
- Migrations moved to a numbered registry that aborts on real errors
  (`backend/migrations/registry.py`), with a schema stamp — the ~90 `ALTER…except: pass`
  boot pattern is gone.
- Daily DB backups + `busy_timeout` landed; dashboard binds `127.0.0.1` by default
  (`config/__init__.py:177-182`); the news-calendar fetch is off the event loop.
- 3,384 lines of dead per-engine `database.py` clones deleted (`da117b6`).
- `FakeMT5Bridge` itself is well built: surface-pinned against both real clients,
  deterministic market, and `inject_error()` designed specifically to make the
  C1/C2 rejection class testable (`fake_bridge.py:18-19`). This is the right
  foundation for the Simon-gated money work.
- The discipline is real: the frozen close path is byte-identical, and PROGRESS.md
  does not claim money fixes it didn't make.

**Cosmetic / neutral:** the doc reorganizations (stage1/2/3 shuffles, spec moves,
handover pack) are most of the commit count. Fine, but they create the *impression*
of remediation velocity (see H-NEW-1).

**Regressed:** one thing — C-NEW-1. Debug mode shipped its UI promise ("no real
orders") before shipping the mechanism that makes the promise true. Everything else
either improved or stood still.

## What is genuinely healthy (unchanged, don't "fix")

- The atomic signal claim (`trade_repo.claim_signal_activation`, `trade_repo.py:350-357`;
  used at `open_from_signal.py:77-79`) — single conditional UPDATE, correct design.
- The frozen close path: `close_trade` raises on broker-close error/False
  (`close_trade.py:113-121`), handles ladder legs (`:96-99, 268-324`), and is
  witnessed by characterization tests.
- `position_sync`'s miss-streak of 2 (`position_sync.py:50,133-141`) and its
  bridge-health check before trusting an empty positions list (`:108-112`).
- The manual-SL plausibility guard (`manual_market_order.py:91-96`) — a real
  incident (2026-07-13, SL=0.5) turned into a durable input check.
- `_place_order`'s pre-flight stack: market-hours, AutoTrading check, lot-step
  normalisation, broker min-stop clamping, fill-mode fallback on *retcode* errors
  (`mt5_bridge.py:644-709`, minus the `None`-retry at `:715-716`).
- `rg_apply_halts_on_close` writing pause flag + reason in one transaction
  (`governor.py:258-278`).
- Debug-mode DB isolation as far as it goes (`config/__init__.py:199-206`) — a debug
  boot can never open the demo/live database.
