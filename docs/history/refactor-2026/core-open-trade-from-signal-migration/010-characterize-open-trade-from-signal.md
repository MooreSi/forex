# 010 — Characterize open trade from signal (back half)

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** places an order via `open_trade` and modifies it via
`bridge.modify_order`/`ea_bridge.update_trade` -- tested against fakes only, never a real/demo
account.

## Decision

Same fake-bridge approach as packs 10/11, extended with `modify_order` call-log capture.
`ea_bridge.set_instance(fake)` for the EA-managed post-fill branches, reset in fixture teardown
(process-wide singleton, same as pack 11).

## Tests first (TDD)

- `tests/core/test_open_trade_from_signal_characterization.py`:
  - Atomic claim: a signal already `status='activating'` raises "duplicate suppressed" without
    calling `open_trade` at all.
  - On an `open_trade` failure (bridge rejects), the signal's status is restored to `'pending'`
    (not left stuck on `'activating'`) and the original exception re-raises.
  - Each of the 6 post-fill strategies: exact SL (and TP1/TP2 for Conservative/Scalp Runner)
    computed from the trade's actual fill price; DB row updated; `bridge.modify_order` called
    with the exact SL; `ea_bridge.update_trade` called (Conservative/Scalp Runner only) when
    `managed_by == "ea"`, never called for a Python-bridge-managed trade.
  - A strategy NOT in the post-fill list (e.g. Scale Out) leaves the DB row's SL/TP exactly as
    `open_trade` set them — no `modify_order` call at all.
  - Background-commentary scheduling fires for a locally-executed trade, is skipped when
    `result.get("executed_remotely")` is true.

## What to do

1. Write the test file using `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to
   a fake test-double (`get_tick`/`place_order`/`modify_order`/`get_account`), `_dpm_candles`,
   and the risk-settings/signal fixtures needed to drive each strategy branch.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed or modified — verified via the fake bridge's/EA's own call
  logs.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

13 tests written in `tests/core/test_open_trade_from_signal_characterization.py`. No
`engine.py` bugs found. One test-design correction: a naive "pre-set the signal to
`status='activating'`" scenario never actually reaches the atomic-claim UPDATE at all — it's
intercepted earlier by the front half's own status validation (`status not in ('pending',
'active')`), which is pack 12's territory, not the atomic claim's. The atomic claim only ever
matters for a genuine TOCTOU race: a signal that IS `'pending'`/`'active'` when this call's own
checks begin, but gets claimed by a second caller before this call's own UPDATE runs.
Reproduced deterministically (without needing real concurrency) by patching
`db_module.get_circuit_breaker_state()` — an early, single call in the front half — with a
side effect that flips the signal to `'activating'` immediately before returning its normal
value, simulating exactly that race window.

All 6 post-fill override branches' exact SL/TP arithmetic (from the actual fill price, not the
pre-fill proxy values) matched hand-computed expectations on the first attempt. Confirmed:
Conservative and Scalp Runner are the only two that call `ea_bridge.update_trade` for
EA-managed trades (to push corrected TPs the EA's own stale in-memory copy would otherwise
never see); GD VIP Runner and Adaptive Runner leave the signal's TP ladder completely
untouched, overriding only SL; a strategy with no post-fill branch (Scale Out) makes zero
`modify_order` calls and leaves the DB row exactly as `open_trade` set it.
