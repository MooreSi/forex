# 050 — Say so on Telegram when a limit order is withdrawn

**Status:** **BUILT 2026-09-10**, tests-first. `python -m tools.checks all` green. **NOT DEMOED** — no message has reached a real Telegram chat.
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

**Written 2026-09-10, red before the fix:**
[`tests/core/test_limit_withdrawn_alert.py`](../../../tests/core/test_limit_withdrawn_alert.py)
— 14 tests, 9 red at the start plus 3 more added for the fill tail. Assertions are on the **rendered
text**, never on "a send was attempted": bugs/038 was a refusal naming the wrong rule and bugs/036 an
IME note promising a follow-up that could not arrive, and a call-counting test passes through both.

Covered: the withdrawal names the direction, the resting price, the channel and the refusing gate's
own words; the re-placement is announced and says how much of the ORIGINAL clock is left; a second
withdrawal and a second re-placement are silent; the count is on the row, not in memory; a fill
reports the total; a clean fill and a single withdraw/replace cycle add nothing (both events were
already announced as they happened, so repeating them would be a third message about the same two);
a sweep that withdraws nothing says nothing; a send failure neither raises out of the sweep nor stops
the order being recorded as withdrawn; and damping never reaches the ORDER — three flaps still leave
`status='withdrawn'` and `withdraw_count=2`.

All four green controls were verified capable of failing by breaking each assertion and re-running.

## What was built (2026-09-10)

**One counter, not two flags.** Migration 38 adds `withdraw_count` to `vantage_pending_orders`. A
withdrawal is the first when the count reads 0; a re-placement is the first when it reads 1, because
the first re-placement can only follow the first withdrawal. That is the whole damping rule, and it
needs no second column and no state a restart could forget.

**On the row, not in a module global** — the decision's own reasoning: a global would restart the
noise after a restart *and* lose the number the fill message is supposed to carry.

`fmt_limit_withdrawn`, `fmt_limit_rearmed` and `fmt_flap_note` live with the rest of the `fmt_*`
family. `_announce` in the sweep makes the send, takes the damping decision as an argument, and never
raises — the sweep runs on a loop and promises not to. A failure is logged at **warning**, not
swallowed: bugs/020 was 107 alerts silently rejected by Telegram.

## What to do

1. ~~Write the tests above; run them; confirm they fail for the right reason.~~ Done 2026-09-10.
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
