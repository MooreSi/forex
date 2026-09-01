# Q008 — Should a zone signal rest as a real broker order?

**Who answers:** Simon. This is a trading-behaviour decision, not a bug.
**Status:** **ANSWERED — A.** Recorded in the file below and in
[questions.md](questions.md).
**Raised:** 2026-08-27, out of the "signals sit in pending and nothing happens"
investigation.
**Touches money:** yes — it changes how and when entries are filled.

---

## What happens today

When a Telegram signal arrives and price is **not yet inside its entry zone**,
the app does not place anything at the broker. It writes a row to
`vantage_signals` with `status='pending'` and a Python loop watches the tick
feed; the moment price comes back into the zone it fills **at market**.

There is exactly one exception. A message in the layout

```
BUY LIMITS GOLD @ 4073/4067 AREA
TP 4076
...
SL 4066
```

places a genuine resting BuyLimit/SellLimit order on the EA, with a 60-minute
TTL, and MT5 does the waiting. That is the Limit Runner strategy, and it fires
on that **message layout** — not on the channel, not on a setting.

So two signals describing the same setup get completely different execution
models depending on how the provider happened to word the message.

## Why it is being asked now

The report was: "the app takes every signal, puts it in pending as a limit
order, then does nothing with them — they don't activate when price comes back
in range, and no limit order is placed on the EA which it should do."

The first half of that was a set of real bugs and they are fixed (see the
session notes and `docs/system/domains/signals/README.md`). The second half —
*"no limit order is placed on the EA, which it should do"* — is not a bug. The
app has never done that for anything except the `[LIMITS]` layout. Making it do
so is a deliberate change to the execution model and it is your call.

## The trade-off, plainly

**A resting broker order fills when price touches, even if the app is down, the
laptop is asleep, or the VPS has dropped its connection.** That is the argument
for it, and it is a strong one.

**A Python zone-wait re-validates at the moment of entry.** Before it fills it
re-checks the R:R gate, the momentum of the last M5 candle, the trading
schedule, the news blackout, the max-open-trades cap and the circuit breaker. A
resting order at MT5 has none of that — it fills the instant price touches, with
no round trip back to the app. `core_pending_order_revalidation.py` periodically
re-checks resting orders and cancels invalidated ones, but that is a poll, not a
gate at the moment of fill.

That difference is exactly why the two paths have different expiry windows: a
re-validated zone signal is allowed to wait hours; a resting order gets 60
minutes.

## The options

- **A. Leave it.** Zone signals stay a Python wait; only the `[LIMITS]` layout
  rests at the broker. *(no change, no demo session needed)*
- **B. Make it a per-channel setting.** "Rest this channel's zone signals at the
  broker" alongside the existing Channel Strategy / IME switches. Channels you
  trust for entry precision get real pending orders; the rest keep the gates.
- **C. Make it global.** Every zone signal becomes a resting BuyLimit/SellLimit.
  Simplest to explain, and it discards the pre-fill gates for every channel.

**Provisional default while this is unanswered: A.** Nothing was changed —
switching a signal from "re-validated market fill" to "unconditional resting
order" is precisely the class of change `docs/system/rules/10-golden-rules.md`
says not to make unattended.

**ANSWER:** _(unanswered)_

---

## If you pick B or C, this also needs deciding

1. **TTL.** Resting orders currently expire after 60 minutes. Zone signals from
   a gd2-format channel are allowed 15 minutes as a Python wait, and Reversal
   Runner's are allowed 4 hours. Which applies?
2. **Which gates survive.** The schedule and news blackout can still be checked
   *before placing*. The momentum check and the R:R gate cannot be checked at
   fill time at all. Is losing them acceptable?
3. **The weekend.** A resting order placed Friday sits over the gap and can fill
   into Monday's open. The Python wait cannot. `should_queue`/
   `queue_closed_market_limit` already handle a closed market for the `[LIMITS]`
   path — that behaviour would extend to everything.
