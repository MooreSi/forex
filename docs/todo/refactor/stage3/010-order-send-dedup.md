# 010 — Order-send dedup: trade id at the broker, checked before every send

**Status:** **code + tests DONE 2026-08-29 (market closed). NOT Done** — the killer
demo against a live EA is still outstanding, and this task is not `done` without it.
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

---

## Built 2026-08-29 (market closed, no demo yet)

### The hole, more precisely than the spec had it

The spec says the fallback can double-fire. Reading the code, it is narrower
and sharper than that:

- For a **template** strategy a timed-out ack already records a placeholder
  and does not retry (hardened after 2026-07-30). That path was safe.
- For a **non-template** strategy the timeout `raise`s, the outer handler
  catches it, logs *"handoff failed — falling back to Python bridge"*, and the
  bridge sends. That is the live hole.

And it was worse than a missing check: the two paths stamped **different
identifiers**. The EA writes `ea:<trade_id[:10]>` on every leg; the bridge
wrote `sig:<signal_id[:8]>`. No check could have correlated them even if one
had existed.

### What was built

`backend/src/services/broker/dedup.py` — `find_trade(bridge, trade_id)` over
open positions, then the last 24h of deals (a trade can fill *and* close while
an ack is outstanding). It answers **three** states:

| State | Meaning | Caller |
|---|---|---|
| FOUND | the broker shows it | adopt, do not send |
| ABSENT | broker reachable, no record | safe to send |
| UNKNOWN | broker could not be asked | see below |

The third state is the point. A broker that could not be asked has not said
no, and collapsing unknown into absent is how a retry doubles an order.

`backend/src/services/trading/send_dedup.py` — the policy: the gate only runs
when the EA was actually asked and did not confirm, so the ordinary path pays
no extra round trip.

Bridge orders now carry `py:<trade_id[:10]>` — the trade id, under a prefix
deliberately distinct from `ea:` because four services parse `ea:` comments to
map a position back onto a template row.

### The limit I did NOT resolve

**UNKNOWN still sends.** Refusing would be safer against duplication, but a
non-template strategy has no placeholder row to reconcile from, so the signal
would stay `pending` and PendingWatcher would re-activate it every 20 seconds
— the failure that turned 5 signals into ~133 opens on 2026-07-30, which is
worse than the duplicate this gate stops.

Handling it properly needs the recorded-as-UNKNOWN state that
[020](020-timeout-means-unknown.md) introduces. It logs loudly, and there is a
test named for the behaviour so it is visible rather than assumed.

### Two existing tests were changed, deliberately

`test_open_trade_characterization.py` and `test_open_trade_surface.py` both
pinned the literal comment `"sig:sig-1"`. That is the behaviour this task
changes by design. They now assert **structurally** — that the comment carries
the trade id this call returned, and does not wear the `ea:` prefix — rather
than against a new literal, which would only say "the code emits what the code
emits".

### Not done

The **killer demo**: pause the demo EA, force an ack timeout, confirm exactly
one position exists and the log shows the fallback adopting. Market closed
until Monday. Until that passes on Simon's terminal this task stays open.

The **magic number** half of the spec is also not done — `place_order` takes
only a comment, so a magic number means changing both bridge programs, and
that cannot be verified without placing an order. The comment alone is
sufficient for the dedup check.
