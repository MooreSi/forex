# Core Scan Messages: Edit/Re-parse Migration

Sub-pack A of `core-scan-messages-migration` (see its README for the full
scoping breakdown). Extracts the dedup/edit-correction state machine
embedded inline in `SimulationEngine._scan_messages` (core/engine.py,
lines 6330-6561) into a standalone module.

Fires whenever a Telegram message's `tg_message_id` already has a
`vantage_tg_signals` row (i.e. this message was seen before — Telegram
delivers an edit as the same message ID with new text). Branches:

- Text unchanged since last seen -> dedup skip.
- Text changed, deterministic re-parse succeeds, same direction as before:
  a full re-parse (SL/TP present) updates all fields; if the existing
  status was `pending_followup` (a partial GD2 entry awaiting SL/TP), this
  promotes the message to the normal execution flow instead of stopping
  here. A parse with no entry data (a non-signal text tweak) updates
  `raw_text` only.
- Text changed, deterministic re-parse succeeds, direction flipped: if not
  yet executed (`status == "new"`), corrects the pending signal in place
  and alerts; if already executed/activated, can't auto-correct — updates
  `raw_text` (so future scans converge) and sends a manual-review warning.
- Text changed, deterministic re-parse fails entirely: if the existing
  status is one of the instant-entry statuses
  (`instant_activated`/`instant_pending`/`instant_historical`), tries an
  instant-entry-trigger-only parse ("Buy Now"/"Sell Now" with no
  SL/TP). If that finds a **direction flip**, this is a real market-order
  correction — finds the matching open trade (by `tg_source` in
  `(channel_name, f"instant:{channel_name}")`) and **closes it** via
  `close_trade` before alerting, since the original instant entry already
  placed a live order in the wrong direction. Same direction (still
  bare) just re-syncs `raw_text`. If the instant-trigger parse also fails
  (or the status wasn't an instant one), falls back to the AI signal
  fallback before giving up — an edit with novel wording fails the
  deterministic parsers exactly like a first-time message would, and
  deserves the same recovery path (`_try_ai_signal_fallback`, already
  extracted). AI success re-enters the same same-direction/flipped-direction
  logic above; AI failure drops the edit (logged, not silently — a message
  ID that never converges would otherwise re-trigger every scan cycle
  forever).

**Real-money surface:** the instant-entry-flip-flatten path calls
`close_trade` on a real open position. Faked in every test here — its own
order-closing behavior is already characterized in
`core-close-trade-migration`.

Reuses already-extracted collaborators: `core_ai_signal_fallback.try_ai_signal_fallback`,
`core_instant_followup.find_and_apply_instant_followup`,
`core_close_trade.close_trade`.

See `PROGRESS.md` for task status.
