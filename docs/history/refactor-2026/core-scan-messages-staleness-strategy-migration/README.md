# Core Scan Messages: Staleness + Strategy Resolution Migration

Sub-pack C of `core-scan-messages-migration` (see its README for the full
scoping breakdown). Extracts two consecutive blocks embedded inline in
`SimulationEngine._scan_messages` (core/engine.py, lines 6809-6982) into a
standalone module.

1. **Staleness guard + recording.** Signals are scalps: an entry zone is
   only valid for minutes. A message older than 4 minutes at processing
   time (Telegram delivery latency + one scan cycle, nothing more -- a
   prior 2-hour window let a 22-minute-old signal execute at market after
   a downtime, straight to SL) is recorded as `historical` and never
   executed, with a one-time "detected but not executed" alert (deduped
   via `INSERT OR IGNORE`'s rowcount, so a re-scan of the same buffered
   message doesn't re-alert). No timestamp at all counts as stale
   (unverifiable age, not a free pass). Otherwise recorded `new` and
   proceeds.
2. **Per-channel strategy + skip-reason resolution.** Resolution order:
   channel override > auto-Claude per-signal evaluation (only when
   auto-execute is on and an AI provider is configured; falls back to the
   channel's last saved recommendation if the AI is unconfigured or the
   per-signal evaluation call raises) > channel's saved AI recommendation
   > global Active Strategy setting. A `"High Risk"` marker anywhere in the
   raw message text overrides all of that to Conservative for just this
   trade. DPM (if globally enabled) overrides the *displayed* strategy
   name to `"DPM"` without changing the underlying `strategy` value used
   for sizing/handler dispatch. Session-gate/pause-state messaging is
   computed here too (used by the final Telegram alert regardless of
   auto-execute state, and by sub-pack D's own execution gate).

**Real-money surface:** none directly -- the AI per-signal evaluation
(`channel_strategy_ai.evaluate_signal_strategy`) only picks a strategy
name, never places an order itself.

See `PROGRESS.md` for task status.
