# Limit orders — decisions to confirm

Plain-English choices to settle before building. Each has a **recommendation** — say "go with the
recommendations" and change only what you disagree with.

Answer inline (write `ANSWER:` under each). Answered items stay, annotated — don't delete them.

## The decisions (quick list)
1. Where is a resting order's template stop measured from?
2. Which toggle turns the widened re-check on?
3. How much does a withdraw/re-arm flap say on Telegram?
4. Does the EA recompile go out on its own, or with the whole pack?

---

## 1. Where is a resting order's template stop measured from?

A template says "stop 60 pips away". Sixty pips from *what*? On a market order the answer is obvious:
from the price you just filled at. A limit order fills later, at a price you name now, which may be
20 points from where the market is sitting when you place it.

- **From the resting price (Recommended)** — the stop ends up 60 pips from where the trade actually
  opens. This is what the template means, and it makes a limit order's risk identical to the same
  template's risk on a market fill.
- **From the tick at placement time** — reuses `resolution.py`'s existing code with no change at all.
  But the stop then sits a distance from the entry that nobody chose: on the 2026-09-10 example it
  would be 13.7 points wrong.

ANSWER:

## 2. Which toggle turns the widened re-check on?

Today the resting sweep only runs when the trend gate (`htf_bias_gate_enabled`) is on, because until
now the bias was the only thing it checked. Once it also checks news, schedule, momentum and R:R,
that coupling means **turning the trend gate off silently turns off the news re-check too**.

- **Its own setting (Recommended)** — one new tunable, "re-check resting orders before they fill",
  default on. The trend gate keeps its own switch and only governs the bias half. Costs one Settings
  entry; see the `/add-tunable` skill.
- **Keep it on the trend gate's toggle** — nothing new to add, but the two are then permanently
  entangled and someone will eventually be surprised by it.
- **Always on, no toggle** — simplest. But every other gate in this system has a switch, and a sweep
  that cancels live orders with no way to stop it is not a thing to ship on a Friday.

ANSWER:

## 3. How much does a withdraw/re-arm flap say on Telegram?

You asked for a message when an order is discarded. With re-arm, one order can be withdrawn and
re-placed several times in an hour — a news window opening and closing, momentum flipping across two
candles. Each of those is, literally, a discard.

- **First withdrawal + first re-placement, then quiet (Recommended)** — you see it happen and you see
  it come back. Further flaps are counted and reported once, in the message when the order finally
  fills, expires or is cancelled for good.
- **Every withdrawal and every re-placement** — complete, and noisy. On a bad news morning this could
  be a dozen messages for one setup.
- **Only the final outcome** — one message when the order fills or expires, summarising what happened
  to it. Quietest, but you lose the ability to see a withdrawal while it matters.

ANSWER:

## 4. Does the EA recompile go out on its own, or with the whole pack?

Task 030 needs the EA rebuilt and redeployed to MT5. That is your action, and it is the slowest part
of this work.

- **With 010-030 together, one demo session (Recommended)** — routing, template management and the EA
  change are one feature; demoing them apart proves less than demoing them together, and 010 on its
  own leaves a resting order managed by the wrong ladder.
- **030 first, on its own** — the EA change is backward-compatible (no template sent means no `tpl_*`
  fields, so today's payload is unchanged), so it could be deployed early and sit dormant. Lower risk
  per step, more steps.

ANSWER:

---

## Quick-confirm checklist
- [ ] 1 — resting price, or tick?
- [ ] 2 — own toggle, shared toggle, or none?
- [ ] 3 — which flap policy?
- [ ] 4 — one demo session, or EA first?
