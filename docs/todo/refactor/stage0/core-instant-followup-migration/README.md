# Core Instant Follow-up Migration

Extracts `SimulationEngine._apply_followup_to_instant_trade`,
`_find_and_apply_instant_followup`, `_ime_timeout_watchdog` (core/engine.py)
into a standalone module. Second and final pack of the IME cluster --
`core-instant-entry-migration` covered the initial market-entry side; this
pack covers what happens once the full follow-up signal (SL/TPs) arrives, or
never does.

  - `_apply_followup_to_instant_trade`: applies a follow-up signal's SL/TP to
    an already-open instant-entry trade. Self-managing strategies
    (Conservative/Conservative Trial, which set their own fixed-point levels
    immediately on fill) acknowledge the follow-up without applying it --
    unless the channel's strategy override has since diverged from what the
    trade was actually opened with, in which case the trade's strategy record
    is corrected and the signal's levels ARE applied after all. A TP-validity
    check auto-spaces six standard TP levels from the actual fill price
    whenever fewer than 2 of the signal's own TPs would land in the
    profitable direction from that fill (common when the follow-up's price
    zone has drifted from where the instant entry actually executed). Routes
    through the already-extracted `core_update_signal.update_signal` when a
    signal record is linked; falls back to a direct DB update + bridge sync
    (with its own BE-Runner-specific "pick the highest safe TP" logic) when
    it isn't.
  - `_find_and_apply_instant_followup`: locates the open instant-entry trade a
    follow-up belongs to (by channel + direction), including a Local/Remote
    sync-forwarding branch for centralized signal generation. Returns whether
    a match was found and applied, so the caller can skip opening a second,
    independent trade for the same signal.
  - `_ime_timeout_watchdog`: a periodic sweep (not itself a loop -- called
    from the existing monitor loop) auto-assigning six standard TP levels to
    any IME trade that's been open 3+ minutes with no follow-up, moving SL to
    breakeven if price has already cleared the auto-assigned TP1.

Every branch's exact numeric output was traced against unmodified `engine.py`
via throwaway scripts before being written into test assertions, same rigor
as `core-instant-entry-migration`.

See `PROGRESS.md` for task status.
