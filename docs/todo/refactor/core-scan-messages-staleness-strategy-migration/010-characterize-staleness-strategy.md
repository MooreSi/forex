# 010 — Characterize staleness + strategy resolution

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** none.

## Decision

No separate original method exists for either block, so characterization
drives the whole `_scan_messages` for one scan cycle with a message that
already cleared sub-pack B's classification (real GD2 signal text), using
a fake bridge whose `get_tick()` returns `None` so sub-pack D's own
(not-yet-extracted) auto-execution block reaches its own early "no live
price" exit harmlessly when a test needs `auto_execute_signals=1` to
reach the per-signal AI evaluation path (only invoked when auto-execute is
on) -- proven safe since `get_open_trades` is also faked to return `[]`,
so no live order is ever attempted.

`telegram_alerts.fmt_signal` is faked to capture its call arguments
directly (`skip_reason`, `strategy_name`) rather than parsing the rendered
alert text, since the resolved strategy name doesn't appear verbatim in
every rendered format.

Every branch pre-traced via throwaway scripts first.

## Tests first (TDD)

- `tests/core/test_scan_messages_staleness_strategy_characterization.py`:
  - Message older than 4 minutes -> recorded `historical`, one alert sent,
    not in `new_signals`.
  - No timestamp at all -> treated as stale (unverifiable age).
  - Fresh message -> recorded `new`, reaches `new_signals`.
  - No channel strategy override -> `strategy` stays the global
    `trade_strategy` risk setting.
  - Override `"auto"`, auto-execute off -> uses the channel's saved AI
    recommendation (`get_channel_strategy_rec`) directly, no live AI call.
  - Override `"auto"`, auto-execute on, AI provider not configured ->
    same fallback (no live AI call).
  - Override `"auto"`, auto-execute on, AI configured, per-signal
    evaluation returns `skip` -> `per_signal_skip` set, downstream
    skip-reason (sub-pack D's own gate) reflects the AI's reasoning;
    strategy left unchanged.
  - Same, evaluation returns a strategy -> `strategy` updated to it.
  - Same, evaluation raises -> falls back to the channel's saved AI
    recommendation, no crash.
  - Specific (non-`"auto"`) channel override -> `strategy` set directly.
  - `"High Risk"` anywhere in the raw text -> forces Conservative
    regardless of any other resolution.
  - DPM globally enabled -> displayed `strategy_name` becomes `"DPM"`
    (the underlying `strategy` value is unchanged).
  - Session not allowed -> skip-reason names the closed market.
  - Trading paused -> skip-reason includes the halt reason and resume
    time.
  - Neither -> default "Auto-execution is OFF" skip-reason.

## What to do

1. Write the test file using a fake `_tg_reader`, a no-tick fake bridge,
   and a faked `telegram_alerts.fmt_signal` call-capture, calling
   `_scan_messages` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- the fake
  bridge's `get_tick()` always returns `None`, keeping sub-pack D's own
  not-yet-extracted auto-execution block a harmless no-op in every test
  here.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

15 tests written in
`tests/core/test_scan_messages_staleness_strategy_characterization.py`,
all green on the first run against unmodified `engine.py` after one
self-caught fixture issue (a bare `mock.Mock()` bridge crashing sub-pack
D's `await self.get_tick()` once `auto_execute_signals=1` was needed to
reach the AI-evaluation path -- fixed with a minimal async fake bridge
whose `get_tick()` returns `None`). No `engine.py` bugs found.
