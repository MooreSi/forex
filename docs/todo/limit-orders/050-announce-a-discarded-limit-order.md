# 050 — Say so on Telegram when a limit order is withdrawn

**Status:** not started
**Depends on:** [040](040-revalidate-before-the-fill.md)
**Real-money surface:** no — it only reports. Still worth care: a message that misstates what happened to an order is worse than no message.
**Leverage:** `telegram/alerts.py` already has the formatter family and the send path.

## Problem

`revalidate_resting_orders` cancels a live broker order and says so only to the log
(`resting_revalidation.py:74-78`). From the user's side an order simply stops existing: no message,
and the next thing they see is the setup not filling when price reaches the zone. Every other
consequential event on this system announces itself — fills, TP hits, SL moves, closes.

Owner, 2026-09-10: *"You should send a telegram message advising if a limit order is discarded on
this basis."*

## Decision

A `fmt_limit_withdrawn` formatter alongside the existing `fmt_*` family, sent from the sweep. It
names the signal, the channel, the resting price, how far price was from it, and **the gate that
refused, in the gate's own words** — the reason string is already threaded through
`cancel_pending_order`, so there is nothing to invent.

A second, quieter formatter for the re-arm, so a withdrawal is never left looking permanent when the
order is back on the book.

Damping matters here. Withdraw-and-re-arm can flap, and each flap is a message. Default: announce the
**first** withdrawal and the **first** re-placement for a given signal, then stay quiet for that
signal until it fills, expires or is cancelled for good — with the flap count included in the final
message so the behaviour is visible without being noisy. Open for confirmation in QUESTIONS.md.

## Tests first (TDD)

- `tests/core/test_limit_withdrawn_alert.py`
  - the message names the direction, the resting price, the channel and the refusing gate's reason
  - a withdrawal sends exactly one message; a re-arm sends exactly one more
  - a second withdrawal of the same signal sends **none**, and the flap count reaches the final
    message instead
  - a sweep that cancels nothing sends nothing
  - a send failure does not raise out of the sweep — the sweep's no-raise promise is the point of
    `resting_revalidation.py`'s docstring, and an alert is not worth breaking it for
- Assert on the rendered text, not on "a send was attempted". `bugs/038` was a refusal message naming
  the wrong rule, and `bugs/036` an IME note promising a follow-up that could not arrive; both are
  this failure mode.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Add `fmt_limit_withdrawn` and `fmt_limit_rearmed` to `telegram/alerts.py`, following the existing
   formatters' conventions — `_md_esc`, `_node_label`, the `event_type` argument to `send_message`.
3. Call them from the sweep in 040, inside its existing per-order `try`.
4. Hold the per-signal announce state wherever 040 holds the withdrawn status, not in a module global
   — a global would not survive a restart, and a restart mid-flap should not restart the noise.

## Where

- `backend/src/services/telegram/alerts.py` — the two formatters
- `backend/src/services/trading/resting_revalidation.py` — the call sites

## Acceptance

- Every withdrawal the sweep performs produces exactly one Telegram message naming the real reason,
  or is deliberately damped by the flap rule.
- No message claims an order was withdrawn when it was not, or claims a reason other than the one
  that fired.
- **The killer test:** the 040 killer scenario — withdraw on news, re-arm 10 minutes later — reads as
  two messages that a person can follow without opening the log.

## Notes

Check the send-dedup path (`backend/src/services/trading/send_dedup.py`) before adding a new
`event_type`; [bugs/028](../bugs/028-one-close-announced-and-booked-twice.md) was one close announced
twice, and [bugs/020](../bugs/020-alerts-were-silently-rejected-by-telegram.md) was alerts silently
rejected by Telegram. Both are worth reading before adding a formatter.
