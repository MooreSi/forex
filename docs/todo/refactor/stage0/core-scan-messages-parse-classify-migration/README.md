# Core Scan Messages: Parse/Classify Migration

Sub-pack B of `core-scan-messages-migration` (see its README for the full
scoping breakdown). Extracts the channel-format-based signal parsing block
embedded inline in `SimulationEngine._scan_messages` (core/engine.py,
lines 6601-6807) into a standalone module.

Runs for every new (non-edit) Telegram message once it's cleared the
per-channel config gate. Resolution order:

1. **Learned rules** (`parse_with_learned_rules`) get first refusal -- a
   format the AI has already confirmed once for this exact channel/message
   shape is more specific than any deterministic gate below it.
2. **`format_ab`** channels: if the text doesn't even match the channel's
   configured prefix/structural markers, try the AI fallback before giving
   up. A match that names a non-XAUUSD currency is recorded
   (`unsupported_currency` status) and alerted -- but only once per
   15-minute window per channel/direction/currency, since providers often
   send a short alert followed by the full signal seconds later as two
   distinct message IDs (the dedup key is extracted from a `"Direction
   BUY/SELL"` label in the text, so it only actually dedupes on channels
   using that label style -- a pre-existing, narrow gap preserved exactly
   as-is, not fixed here). A currency match that parses cleanly proceeds;
   one that fails deterministic parsing tries the AI fallback, then queues
   as unrecognised.
3. **`gd2`** channels: if the message doesn't match GD2's own trigger
   patterns at all, try the AI fallback. A match that fails full parsing
   tries a **partial** parse (direction + entry range, no SL/TP yet --
   GD2 often sends these first and edits in the levels seconds later,
   recorded as `pending_followup` for sub-pack A's edit handler to
   promote later); failing that, a bare instant-entry trigger with no
   levels at all is silently skipped (not queued -- IME's own dispatch
   already handles this shape when IME is on); only genuinely garbled
   content that fails every check tries the AI fallback, then queues as
   unrecognised.
4. **`auto`** channels: tries `format_ab` first (if a prefix is
   configured and matches), then `gd2`, then the AI fallback -- silently
   drops on total failure rather than queuing (an auto-format channel
   producing noise isn't actionable the way a configured-format channel
   failing its own format is).

**Real-money surface:** none directly -- parsing/classification and DB
recording only, no order placed or modified.

Reuses the already-extracted `core_ai_signal_fallback.try_ai_signal_fallback`/
`queue_unrecognised`.

See `PROGRESS.md` for task status.
