# Trading-Safety and Financial-Risk Review — 2026-08-08

Read-only review of the live-money surfaces of the MT5 XAUUSD trading system at
`c:\dev\forex\app`. No code was run, no MT5 contact was made; findings are from
file reads and greps only. Line numbers refer to the files as of this date.

## Summary

The order/close core is in better shape than most systems of this size: there is
an atomic signal claim for duplicate suppression, a miss-streak guard before
believing a broker-side close, no automatic HTTP retries around `order_send`,
and the frozen close path (`close_trade`, `record_close`, `_make_close_trade_ctx`,
`partial_close_trade`) is intact in `services/trading/close_trade.py` /
`partial_close.py` with thin verbatim wrappers in `runtime.py` and a
characterization-test witness in `tests/core/`.

The dominant residual risks are all in the *ambiguity windows* around the
broker call, not in the happy path:

1. **Timeout-then-fallback double-fire** — an EA `open_trade` ack that arrives
   after the 5 s wait is treated as failure and the same order is re-sent via
   the Python bridge (two live positions). The same pattern exists at the
   signal level: a slow broker fill that outlives the 15 s HTTP timeout
   restores the signal to `pending`, making it re-openable.
2. **DB-close on ambiguous broker state** — two non-frozen close paths
   (`check_profit_close_target`, `reconcile_sl_hit`) can mark a trade closed in
   the DB while the broker position is still open, with no miss-streak guard.
3. **Duplicated close logic outside the frozen path** — the profit-close and
   SL-reconcile paths in `monitor_loop.py` re-implement "close position +
   record_close" without the ladder-leg handling and error-raising that
   `close_trade()` has; a profit-close on an Adaptive Runner ladder trade would
   orphan legs 2..N.
4. **`record_close` has no idempotency/status guard** (acknowledged in a code
   comment), so any two of the several closers racing produces double-counted
   P&L.
5. Most global risk brakes (Risk Governor, circuit breaker, daily loss, total
   drawdown) are **opt-in flags, default OFF**; the always-on protections are
   only `max_open_trades` (default 1), `max_lot_size` (default 0.10) and the
   `max_risk_per_trade_pct` cap inside `suggest_lot_size`.

## Money paths mapped

```
Signal sources                       Sizing & gates                    Wire to MT5
--------------                       --------------                    -----------
Telegram parse ─┐
Breakout gen  ──┤ (bo_live_execution)
Bounce gen ─────┤ (sg_live_execution)   resolution.resolve_open_trade_params
Reversal gen ───┤ (re_live_execution)     └ suggest_lot_size (fees_sizing.py)
Manual UI ──────┤                          └ governor.rg_size_and_check (if RG on)
Bot commands ───┘                          └ check_pre_trade_filters (R:R, dir cap)
        │                                        │
        ▼                                        ▼
open_from_signal.open_trade_from_signal   [atomic claim: claim_signal_activation]
        │
        ▼
services/trading/open_trade.open_trade
   ├ stand-down gates (paired node)  ├ trading pause  ├ circuit breaker
   ├ max_open_trades gate
   ├ EA path:   ea_bridge.EABridge.open_trade ── TCP 127.0.0.1:9101 ──▶ ForexTraderBridge.mq5 (trade.Buy/Sell)
   └ HTTP path: mt5_client.place_order ── HTTP 127.0.0.1:9000 ──▶ mt5_bridge.py _place_order (mt5.order_send)
        │
        ▼
trade_repo.insert_trade_and_activate_signal  (single transaction)

Ongoing management (per-tick):
monitor_cycle ── check_sl / reconcile_sl_hit / check_profit_close_target
             ── strategy handlers (partial_close / modify_order)
positions/safety_net (modify_order to BE)   positions/tp_ladder (partial_close)
broker/position_sync (reconcile DB vs broker; miss-streak = 2; imports untracked)

Close (FROZEN): close_trade / record_close / close_all_ladder_legs
  (services/trading/close_trade.py; partial_close_trade in partial_close.py;
   wrappers runtime.py:497-506; ctx factory runtime.py:420)
```

## Findings

### Critical — could lose money or fire unintended orders

**C1. EA ack timeout falls back to a second live order (double-fire).**
`backend/src/services/trading/open_trade.py:300-335`: the EA handoff
`await _ea.open_trade(...)` waits 5 s for the ack
(`backend/src/services/broker/ea_bridge.py:170,253`). On `TimeoutError` the
`except Exception` at `open_trade.py:321-324` logs "falling back to Python
bridge" and proceeds to `bridge.place_order(...)` at line 334. The EA side
(`mql5/ForexTraderBridge.mq5:411-523, HandleOpenTrade`) has **no dedup on
`trade_id`** — it places the market order first and only then sends the ack. A
slow broker fill (>5 s is realistic during news on XAUUSD), a stalled socket
after the EA already executed, or a lost ack line therefore produces **two live
positions for one signal**: one EA-managed (unknown to the DB, later imported
by the untracked-position importer as a *third*, independently managed trade —
see H6) and one Python-bridge trade. Nothing reconciles the pair.

**C2. Order-send ambiguity re-arms the signal (double-fire, HTTP path).**
`mt5_client.place_order` uses a 15 s timeout
(`backend/src/services/broker/mt5_client.py:292`) and returns `{"error": ...}`
on *any* exception, including a timeout where `mt5.order_send` actually
succeeded at the broker. `open_trade.py:339-341` raises, and
`open_from_signal.py:95-98` then calls
`trade_repo.restore_signal_after_failed_open` (trade_repo.py:360) putting the
signal back to `pending` — where the pending-activation watcher can legally
open it again. Result: filled-but-unrecorded position + a second fresh order.
There is no idempotency key on `POST /order` (mt5_bridge.py:1252-1262), so the
bridge cannot detect the resend either.

**C3. Fill-mode retry loop in the bridge can re-send after a `None` result.**
`mt5_bridge.py:711-728` (`_place_order`): the loop over
RETURN/IOC/FOK re-invokes `mt5.order_send(request)` when the previous call
returned `None`. `order_send` returning `None` means "no response" (IPC
error/timeout), **not** "order rejected" — the first request may have reached
the server. The retry then submits a second real market order. (Retcode-based
retries in `_FILL_ERRORS` are safe; the `result is None: continue` branch at
line 715-716 is the dangerous one.)

### High — could mis-size, fail to close, or corrupt position truth

**H1. Profit-close records a DB close even when the broker close failed.**
`backend/src/services/positions/monitor_loop.py:119-134`
(`check_profit_close_target`): `bridge.close_position` errors are only logged
(`except ... log.warning`, line 126-127) and a non-`success` response is
ignored; `record_close` runs unconditionally at line 128. A bridge outage at
the wrong moment leaves a **live, open broker position that the app believes is
closed** — its ticket stays in `fetch_known_mt5_tickets` (broker/repo.py:233),
so the untracked importer will not re-adopt it: it is permanently unmanaged
except for its broker-side SL (which strategy `no_sl_scale` does not have).
Contrast with the frozen `close_trade` (close_trade.py:113-121), which
correctly raises on error/`success is False`.

**H2. Profit-close and SL-reconcile bypass the frozen close path's ladder
handling.** `close_trade()` explicitly closes every Adaptive-Runner ladder leg
(close_trade.py:96-99, 268-324) precisely because `row["mt5_ticket"]` is only
the anchor. `check_profit_close_target` (monitor_loop.py:119-128) and
`reconcile_sl_hit`'s fallback (monitor_loop.py:93-98) close/record against the
anchor ticket only and mark the parent closed — orphaning legs 2..N from all
Python management (the 2026-07-17 incident class the position_sync comment
describes). This is exactly the "duplication/divergence next to the frozen
path" the review was asked to look for: two younger, near-copies of the close
sequence without its safeguards.

**H3. `record_close` has no idempotency or status guard.**
`close_trade.py:136-151`: unlike `close_trade` (checks `status != "open"`,
line 90-91) and `partial_close_trade` (partial_close.py:23-24), `record_close`
never checks trade status before applying `apply_full_close`. The position_sync
docstring itself states "_record_close() has no idempotency guard_"
(position_sync.py:70-75). At least five callers can race to close the same
trade (EA `trade_closed` event, position_sync, reconcile_sl_hit, profit-close,
manual close). The EA-vs-sync race is mitigated by excluding `managed_by='ea'`
from the sync poll, but reconcile_sl_hit and profit-close run **before** the
EA-managed skip in `monitor_cycle.py:144-166`, so an EA-managed trade can still
be double-closed in the DB (double-counted P&L, wrong circuit-breaker
outcomes).

**H4. A single ambiguous empty `get_positions()` can record a local close.**
`reconcile_sl_hit` (monitor_loop.py:56-98): `mt5_client.get_positions` returns
`[]` on any exception (mt5_client.py:273-282). An empty list makes
`int(mt5_ticket) in live_vol` false, skipping the "deferred" branch, and the
function falls through to `record_close` — no miss-streak, unlike
position_sync's threshold of 2. For trades whose broker-side SL exists this
usually only front-runs reality; for `no_sl_scale` trades (no broker SL) it
can close the DB record while the broker position stays open and unmanaged.

**H5. Close/partial-close use only `ORDER_FILLING_IOC` — no fill-mode
fallback.** `mt5_bridge.py:799` (`_close_position`) and `:839`
(`_partial_close`) hardcode IOC, while `_place_order`'s own comment
(line 689-691) says Vantage typically requires `ORDER_FILLING_RETURN`. If the
broker rejects IOC (retcode 10030), **every close fails** while opens succeed —
the worst asymmetry a trading system can have. Also `_close_position` returns
the pre-trade tick as `close_price` (line 787, 803) rather than
`result.price`, so recorded P&L ignores close slippage.

**H6. Untracked-position importer auto-adopts any broker position into active
management.** position_sync.py:245-268: any position not in
`fetch_known_mt5_tickets` — including a manual trade placed in the terminal, or
the orphaned first leg of a C1/C2 double-fire — is imported with the *default
strategy* and thereafter actively managed (partial closes, SL moves, profit
close) by the app. Amplifies the double-fire findings and can surprise a human
who opens a personal position in the same terminal.

**H7. Sizing balance falls back to the drifting simulation ledger.**
`get_trading_balance` (close_trade.py:74-84) falls back to
`vantage_simulation_account` when the bridge is unreachable — a ledger the
code itself documents as having drifted $707 vs $1122 real
(governor.py:218-227). A trade sized during a bridge blip uses the wrong
balance for risk-% sizing.

### Medium — weaker guarantees than intended

**M1. Most kill-switches are opt-in config, defaults OFF.** Daily-loss halt,
total-drawdown halt, loss-streak cooldown all live behind
`risk_governor_enabled` (record_close → `rg_apply_halts_on_close`,
close_trade.py:229-240; governor.py:218-278); the consecutive-loss circuit
breaker behind `circuit_breaker_enabled` (circuit_breaker_repo.py:55-80,
default 0). They are enforced in code once enabled (pause flag checked in
open_trade.py:181-198), but a fresh install trades with only
`max_open_trades=1`, `max_lot_size=0.10` and the `max_risk_per_trade_pct` lot
cap. Confirm the live install has RG + CB enabled.

**M2. Min-lot floor overrides the risk ceiling in `suggest_lot_size`.**
fees_sizing.py:80-86: `lot = max(min_lot, min(lot, round(risk_capped_lot, 2)))`
forces 0.01 lots even when the risk-capped size is below 0.01 — on a small
balance with a wide stop the "hard ceiling" is silently exceeded. The Risk
Governor path does the right thing and *rejects* instead
(governor.py:182-187). Divergent behavior between the two sizers.

**M3. Directional cap hardcoded in the RG sizer.** governor.py:207-213 uses a
literal `>= 2` while `check_pre_trade_filters` (governor.py:135-143) reads the
`max_unprotected_trades` tunable. Raising the tunable above 2 silently does
nothing when the Risk Governor is enabled; lowering it below 2 is not honored
by the RG path.

**M4. Max-open-trades gate is check-then-act across an await.**
open_trade.py:203-206 counts open trades, then awaits tick fetch/EA/bridge
before the row insert at line 349 — two concurrent opens (e.g. Telegram signal
+ pending-activation watcher on different signals) can both pass the gate and
exceed `max_open_trades`.

**M5. Broker-day boundary hardcoded UTC+3.** governor.py:148-152
(`rg_day_start_ts`) assumes the broker is permanently UTC+3; MT5 brokers
typically flip UTC+2/UTC+3 with US DST. For part of the year the "daily" loss
limit window is offset by an hour. (The candle code, by contrast, measures the
offset live — mt5_bridge.py:462-511 — and documents why assuming a constant is
wrong.)

**M6. EA bridge TCP port has no authentication.** ea_bridge.py:80 listens on
127.0.0.1:9101 and accepts the first connection as "the EA"; the same is true
of the HTTP bridge on :9000, whose `POST /order` any local process can call.
Localhost-only, so exposure requires a compromised machine, but there is no
shared secret at either boundary of the money wire.

**M7. Clock-skew sensitivity in tick timestamps.** `Tick.timestamp` comes from
MT5 server time while freshness checks (`max_signal_age_s`, safety-net windows)
compare against local `time.time()`. The candle-range code compensates;
signal-age staleness checks should be confirmed to use ingestion time, not
broker tick time.

### Low

**L1. `close_trade` reads the trade row synchronously on the event loop.**
close_trade.py:89 calls `trade_repo.get_trade(trade_id)` directly (not via
`to_db_thread`), unlike `record_close` (line 137). Latency, not correctness —
and it is part of the frozen path, so leave it unless the owner reshapes it.

**L2. Floats everywhere for money.** Known and documented
(golden rule 5; `docs/decisions/`). Rounding is consistent (2 dp prices for a
2-digit symbol, 4 dp P&L/lots; lots rounded to broker `volume_step` in
mt5_bridge.py:657-659 and 820-822). No new defects found, but the epsilon
comparisons (`0.001` lots in position_sync/reconcile) are load-bearing —
do not "tidy".

**L3. Signal engines' live execution is flag-gated but shares the live
account.** `test_signal` (Bounce) `_execute_live`
(test_signal_live_execute.py:22-127) runs only when `sg_live_execution` is set
(test_signal_service.py:264); Breakout gates on `bo_live_execution`
(breakout_signal_live_execute.py:34); Reversal on `re_live_execution`
(reversal_engine_live_execute.py:38). All route through the main engine's
`open_trade_from_signal`, so every gate in the Findings above applies. There is
no separate demo endpoint a "test" signal could accidentally cross from —
demo vs live is purely which MT5 account the terminal is logged into. The
naming (`test_signal`) is the only hazard: it is a live-capable engine.

## Recommendations (prioritized)

1. **Kill the timeout-equals-failure assumption on order sends (C1, C2, C3).**
   - Before the Python-bridge fallback in `open_trade.py:333`, and before
     restoring a signal to `pending` after an open failure, query broker state
     (positions/deal history filtered by the `ea:`/`sig:` comment or magic) to
     confirm no fill exists for this `trade_id`/`signal_id`.
   - Add `trade_id` dedup in `HandleOpenTrade` (reject or re-ack if
     `FindManagedByTradeId` matches) so a resend is safe by construction.
   - In `mt5_bridge._place_order`, stop retrying after `order_send` returns
     `None`; return an explicit "unknown outcome" status the caller must
     reconcile, never treat as clean failure.
2. **Route profit-close and SL-reconcile full closes through `close_trade()`**
   (or at minimum: raise on broker-close failure, handle ladder legs, and add a
   miss-streak before trusting an empty `get_positions()`) (H1, H2, H4). This
   is a frozen-path-adjacent change: owner sign-off + demo session required.
3. **Add a status guard to the closers that lack one** — a conditional
   `UPDATE ... WHERE status='open'` claim before `apply_full_close`, mirroring
   `claim_signal_activation` (H3). Touches `record_close`: needs the same
   sign-off + demo protocol.
4. **Give `_close_position`/`_partial_close` the same fill-mode fallback as
   `_place_order`, and report the actual `result.price`** (H5).
5. **Enable-and-verify the brakes on the live install**: risk_governor_enabled,
   circuit_breaker_enabled, sensible max_daily_loss_pct /
   max_total_drawdown_pct; consider making a minimal daily-loss halt
   unconditional in code (M1).
6. Fix the small sizing divergences: reject instead of flooring to 0.01 in
   `suggest_lot_size`, read `max_unprotected_trades` in `rg_size_and_check`
   (M2, M3).
7. Make the untracked-position importer opt-in or quarantine imports as
   "observe-only" until confirmed (H6).
8. Derive the broker-day offset live (as the candle code already does) instead
   of hardcoding UTC+3 (M5).

## Open questions for the owner

1. Are `risk_governor_enabled` and `circuit_breaker_enabled` actually ON in the
   live installs (Mac and VPS)? The code enforces them only when set.
2. Has an EA-ack-timeout double-fire (C1) ever been observed? The
   `[EA-diag]` TEMP log at open_trade.py:246-253 suggests EA handoff was
   already misbehaving on 2026-07-17 — was that diagnosed?
3. Is the profit-close target (`profit_close_usd`) ever used with Adaptive
   Runner ladder trades? If yes, H2 is live today, not theoretical.
4. `_close_position` hardcodes IOC — has a full close ever failed with retcode
   10030 on Vantage? If RETURN is the broker's required mode, H5 needs fixing
   before it is discovered the hard way.
5. Is the untracked-position importer intended to adopt *manual* terminal
   trades into automated management, or only to recover ticket-rotation cases?
6. Vantage server timezone: fixed UTC+3 year-round, or DST-following (M5)?
7. The Mac/VPS pairing docs say the forwarding condition in `open_trade()` and
   `instant_followup` "must stay in sync" — is there a test that asserts the
   two conditions match, or is it manual discipline?
8. `restore_signal_after_failed_open` makes MT5-rejected signals retryable by
   the pending watcher — is a cap on re-attempts per signal wanted, so a
   repeatedly half-failing broker session cannot spray orders?
