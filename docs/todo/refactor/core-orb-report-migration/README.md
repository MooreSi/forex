# Core ORB Report Migration

Extracts `SimulationEngine.build_orb_report`, `_get_orb_target_multiple`,
`_backtest_orb_target_multiple`, `_orb_auto_execute` (core/engine.py) into a
standalone module. Third pack of the broader "finish everything off" push
through the remaining `core/engine.py` subsystems, continuing from
`core-ai-signal-fallback-migration`. Not to be confused with
`core-orb-fixed-handler-migration` (the already-extracted `_handle_orb_fixed`
TP/SL strategy handler, a different subsystem entirely -- this pack covers the
London-open Asian-range breakout report and its auto-execute side effect).

  - `build_orb_report`: computes the Asian-session (00:00-08:00 UTC) reference
    range, a volume profile (POC/VAH/VAL) over it via the module-level
    `_compute_volume_profile` helper (ported verbatim, pure, no `self`), and --
    once London has opened and price has broken one side -- an entry zone,
    stop, and target derived from the empirically-backtested target multiple.
  - `_get_orb_target_multiple` / `_backtest_orb_target_multiple`: a once-daily
    cached backtest measuring, over the account's own recent gold history, how
    far price travelled past the Asian range on days it cleanly broke one side
    only, expressed as a multiple of that day's range height. Falls back to
    the standard 2.0x ORB-literature default with fewer than 8 clean-breakout
    samples.
  - `_orb_auto_execute`: places the report's recommended trade as a pending
    zone-entry signal (not a market order) when the auto-execute toggle is on,
    gated by an active-trader-node / centralized-signal-generation matrix so
    exactly one node ever acts even when the report itself runs unconditionally
    on both Mac and VPS.

All datetime-dependent behavior (`datetime.now(timezone.utc)`) is controlled in
tests via `unittest.mock.patch("forex_trader.core.engine.datetime")` (mirrored
as `core_orb_report.datetime` post-extraction) -- every scenario's expected
values were traced against unmodified `engine.py` with concrete candle/tick
fixtures before being written into test assertions, given the calendar-window
and volume-profile math involved.

See `PROGRESS.md` for task status.
