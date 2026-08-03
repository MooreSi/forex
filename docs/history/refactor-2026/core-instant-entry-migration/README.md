# Core Instant Entry (IME) Migration

Extracts `SimulationEngine._process_instant_entry` (core/engine.py) into a
standalone module. First of two packs covering the IME (Instant Market Entry)
cluster -- this pack handles the initial market-entry side (a bare "XAU
Buy/Sell Now" Telegram message with no levels yet); the follow-up-application
side (`_apply_followup_to_instant_trade`/`_find_and_apply_instant_followup`/
`_ime_timeout_watchdog`) is `core-instant-followup-migration`, a separate pack
given the combined size (712 lines across both). Fourth pack of the "finish
everything off" push through `core/engine.py`'s remaining subsystems,
continuing from `core-orb-report-migration`.

`_process_instant_entry` is the highest real-money-risk piece migrated so far
in this push: unlike the DPM/AI-fallback/ORB packs (DB-only), it places a
genuine MT5 market order via the already-extracted `core_open_trade.open_trade`
(pack 11), which is treated as a faked collaborator here (mocked in tests, the
same way `dpm_engine.compute_adaptive_params` was faked for the DPM handler)
rather than exercised for real -- its own extraction pack already characterized
its behavior.

Flow: staleness guard (4-minute window) -> auto-execute toggle -> session
gate -> live-tick requirement -> spread guard -> strategy resolution
(channel override / "auto" -> last AI rec / per-message "high risk" ->
Conservative) -> max-open-trades gate -> one of three lot-sizing paths
(Risk-Governor ATR-based, fixed-lot-with-$150-cap, or risk-pct-based) ->
`open_trade` -> strategy-specific post-fill SL/TP overrides for
Conservative/Scalp Runner (fixed points from fill) and Conservative Trial
(fixed six-tier ladder from fill) -> Telegram notifications. Any exception
during/after `open_trade` rolls back the provisional signal row and marks the
originating Telegram-signal row `instant_failed`.

Every branch's exact numeric output (lot sizes, SL distances, TP levels) was
traced against unmodified `engine.py` via throwaway scripts before being
written into test assertions, given how many sizing sub-paths interact.

See `PROGRESS.md` for task status.
