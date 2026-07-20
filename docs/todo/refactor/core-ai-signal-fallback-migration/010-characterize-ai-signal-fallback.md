# 010 — Characterize AI signal fallback

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** modifies a live order's SL via `bridge.modify_order` (SL
adjustment path only) -- tested against a fake bridge only. `_try_ai_signal_fallback`
itself never places/closes/modifies an order directly.

## Decision

`ai_signal_extractor.classify_message`/`claude_ai.classify_unknown_message` are faked
via `unittest.mock.patch.object` -- already-extracted, stable, pure-from-this-pack's-
perspective collaborators, same treatment as `dpm_engine.compute_adaptive_params`.
`_is_active_trader_node()` is taken as an explicit `is_active_trader_node: bool`
parameter rather than extracted here (it belongs to the separate startup/lifecycle
cluster; this pack only needs its already-computed answer). The Local/Remote sync
mirror in `_push_ai_recovered_created` is left calling the real `sync.server`/
`sync.client` modules -- both gracefully no-op with no server/client running (confirmed:
`sync.server.get_instance()` returns `None` when uninitialized; `sync.client.get_instance()`
returns a client whose `conn_state` is not `CONN_CONNECTED` with nothing started), matching
the original code's own defensive try/except design, so nothing needs faking there.

## Tests first (TDD)

- `tests/core/test_ai_signal_fallback_characterization.py`:
  - `_try_ai_signal_fallback`:
    - Not the active-trader node -> returns `None` immediately, no dedup check recorded,
      no AI call made.
    - Already dedup-checked for this (tg_id, text) -> returns `None`, no AI call made.
    - Message mentions a non-XAUUSD currency -> returns `None` via the cheap pre-check,
      no AI call made.
    - AI call raises -> returns `None`; the dedup check is NOT recorded (so it's retried
      next cycle).
    - AI call succeeds, result is `None` (not a signal, not an adjustment) -> dedup check
      IS recorded, returns `None`.
    - AI call succeeds, `kind == "sl_adjustment"` -> saves the recovered SL-adjustment row,
      pushes the recovered-created mirror (no-op in test env), applies the SL adjustment,
      returns `None` (not a new entry signal).
    - AI call succeeds, ordinary signal result -> saves the recovered signal row, pushes
      the recovered-created mirror, returns the result dict unchanged.
  - `_apply_sl_adjustment`:
    - No matching open trade for the channel -> no-op, no bridge call.
    - New SL already matches the trade's current SL (within 0.011) -> no-op.
    - Applies cleanly: `bridge.modify_order` called (when `mt5_ticket` present), DB
      `stop_loss` updated, a success Telegram alert scheduled.
    - No `mt5_ticket` -> DB still updates, bridge never touched.
    - Dedup via `try_claim_sl_adjustment` returning `False` (already claimed this tg_id) ->
      no-op, no bridge/DB touch at all.
    - Bridge raises during apply -> a failure Telegram alert is scheduled instead; DB is
      NOT updated (the DB write happens after the bridge call inside the same try block).
  - `_queue_unrecognised` / `_analyse_unrecognised_message`:
    - New unrecognised message -> a `channel_unrecognised_messages` row is saved and an
      analysis task is scheduled (tested by directly calling `_analyse_unrecognised_message`,
      not by waiting on the fire-and-forget task -- same convention as prior packs for
      `asyncio.create_task` side effects).
    - Message already queued for this tg_id -> no new row, no analysis task scheduled.
    - `_analyse_unrecognised_message` success path -> `claude_ai.classify_unknown_message`
      called, the row's `claude_analysis` column updated with the JSON result.
    - `_analyse_unrecognised_message` exception path -> the row's `claude_analysis` is
      updated with an error payload instead of raising.

## What to do

1. Write the test file using a fake bridge (`modify_order`) and
   `unittest.mock.patch.object(ai_signal_extractor, "classify_message", ...)` /
   `patch.object(claude_ai, "classify_unknown_message", ...)`, calling the methods via
   `SimulationEngine.__new__(SimulationEngine)` with `_cfg = {}` and
   `_is_active_trader_node` patched/stubbed to return the desired boolean per scenario.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified — verified via the fake bridge's call
  log.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

17 tests written in `tests/core/test_ai_signal_fallback_characterization.py`,
all green against unmodified `engine.py`. No `engine.py` bugs found. No
recurring `partial_close_trade`-style quirk here (this cluster never
partial-closes; the only order mutation is a plain `bridge.modify_order` SL
change, with the DB write happening after the bridge call inside the same
try block -- confirmed via a dedicated test that a bridge exception leaves
the DB untouched).

`_is_active_trader_node()` taken as an explicit `is_active_trader_node: bool`
parameter in the extraction, not re-extracted here -- it belongs to the
separate startup/lifecycle cluster; this pack only needs its already-computed
answer, same pattern as prior packs treating out-of-cluster dependencies as
injected values.

`_queue_unrecognised` is a synchronous method that internally calls
`asyncio.create_task(...)` -- tested by running it inside an already-running
event loop and yielding once (`await asyncio.sleep(0)`) so the scheduled task
gets created (and its target mocked, so it's assertable), rather than
depending on the fire-and-forget task actually completing -- same convention
used for `asyncio.create_task` telegram-alert side effects throughout the
whole handler-cluster series.

`vantage_simulated_trades.signal_id` is `NOT NULL` -- the open-trade test
helper needs a `vantage_signals` row inserted first, same as every trade-
handler pack's helper.
