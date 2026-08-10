# 010 — Order-send dedup: trade id at the broker, checked before every send

**Status:** not started
**Depends on:** none
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo session.
**Layer:** service (+ the two bridge programs)
**Leverage:** existing broker read calls in `backend/src/services/broker/`; SPEC-002 design

## Problem

One signal can become two live orders (review risk C1): `open_trade.py:300-335` waits 5s for the EA
to ack, then falls back to sending via the Python bridge — but the EA
(`mql5/ForexTraderBridge.mq5:411`) has no trade-id dedup, so a merely-slow EA means both orders
fill. Nothing anywhere stamps a client id on the order that the broker echoes back, so no send path
*can* check "did I already place this?".

## Decision

Stamp the signal's id into both the order comment and the magic number on every send path (EA and
bridge). Before any send — and especially in the ack-timeout fallback — query open positions +
recent deals for that id; if present, adopt instead of place. Chosen over "just lengthen the ack
timeout" because a timeout of any length still races; only broker-visible identity closes the hole.

## What must NOT change

- The frozen close path — untouched.
- Sizing, SL/TP computation, signal claim logic — byte-identical.
- Existing close-path witness tests pass unmodified.
- The EA's order-execution logic beyond reading/echoing the id.

## Tests first (TDD)

- `tests/trading/test_order_send_dedup.py::test_order_send_carries_trade_id` — every send request
  carries the signal id in comment and magic — wiring
- `::test_ea_timeout_fallback_dedups_before_send` — fake broker holds a position with the id; the
  fallback adopts it and sends nothing — behaviour
- `::test_fallback_sends_when_id_confirmed_absent` — fake broker empty; fallback sends exactly once — behaviour
- `::test_dedup_scans_recent_deals_not_just_positions` — id present only in deals history (filled
  then closed) still blocks a re-send — boundary
- `::test_dedup_detector_can_actually_fail` — negative control: with the id genuinely absent, the
  detector reports absent (proves the "found" assertions can fail)

All against the existing MT5 fakes; no real or demo MT5 order.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Thread the signal id into the order request structs on both send paths
   (`open_trade.py`, `mt5_bridge.py`); have the EA echo it (`ForexTraderBridge.mq5`).
3. Add `broker/dedup.py` (or extend an existing broker query module): `find_trade(trade_id)` over
   open positions + last-24h deals (window per QUESTIONS.md #1/#2 answers).
4. Gate the ack-timeout fallback in `open_trade.py:300-335` on `find_trade` returning absent;
   on found → adopt (record the existing ticket), do not send.
5. `python -m tools.checks all` — suite, four gates, coverage ratchet, boot smoke.

## Where

- `backend/src/services/trading/open_trade.py` — fallback gate, id stamping
- `backend/src/services/broker/` — the `find_trade` query
- `mt5_bridge.py` — id stamping on bridge sends
- `mql5/ForexTraderBridge.mq5` — read + echo the id (no other EA change)

## Acceptance

- No send path can fire while the broker already shows the trade id.
- **The killer test (demo session):** force an ack timeout against the demo EA (e.g. pause the EA);
  exactly one demo position exists afterwards, and the log shows the fallback adopting, not sending.
- `python -m tools.checks all` green, real output pasted into PROGRESS.md.

## Notes

- QUESTIONS.md #1 (comment vs magic vs both) and the deals-history scan window (starting value 24h)
  must be answered before step 3 is final.
- The EA change is deliberately minimal; EA-side dedup logic beyond echoing the id is out of scope.
- Coordinates with 020 — both edit `open_trade.py`; land 010 first (README roadmap order).
