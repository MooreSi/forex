# Q009 — When a signal's zone is breached before entry, drop it or queue it?

**Who answers:** Simon (this is a trading stance, not a technical choice).
**Status:** the app currently DISCARDS the signal entirely. Nothing is
changed; you choose whether that stays.
**Raised:** 2026-08-28, from a real signal during the demo session — Simon
asked the question unprompted while watching it happen.

## What happened, exactly

A live Gold Diggers VIP signal arrived:

```
SELL   entry 4537.00 – 4539.00   SL 4544.00
TP1 4535  TP2 4533  TP3 4531  TP4 4529  TP5 4527  TP6 4525  TP7 4522
```

Price at that moment was **4540.45** — above the entry zone, and 3.55 below
the stop. The app skipped it:

> Auto-execution skipped — SELL zone $4537.00–$4539.00 already breached
> (price $4540.45); setup invalidated.

## Why it skipped, and why that part is right

The stop sits ABOVE a sell zone. Price at 4540.45 has therefore moved
*against* the trade, toward the stop, before any entry existed. Selling at
4540.45 would leave 3.55 of stop instead of the 5.00–7.00 the signal
specified — a materially different trade from the one the channel sent.

The check is symmetric for buys (price falling below the zone, toward a stop
underneath). It is not "the price ran away to somewhere better"; it is "the
market moved the wrong way first".

## The actual question

**The signal is not queued. It is dropped.**

Confirmed at the time: no `vantage_signals` row was created at all. The
pending-signal watcher only ever looks at `vantage_signals` rows with
`status='pending'`, so there is nothing for it to find. If price falls back
into 4537–4539 five minutes later, **nothing fires**. The signal is gone.

Both readings are defensible:

- **Discard (current).** Price pushing toward the stop before entry is
  evidence against the setup. A channel's zone is a statement about a moment;
  once the market has moved through it the moment has passed.
- **Queue.** If price genuinely returns to 4537–4539, the entry, the stop and
  all seven targets are exactly as the channel specified. Nothing about the
  original trade has changed. Dropping it means missing a valid fill for a
  condition that has since resolved itself.

## Options

- **A. Keep discarding** *(current behaviour, nothing changes)*
- **B. Queue it as pending, and let it activate if price re-enters the zone**
  *(a real behaviour change on the money path — would need building
  test-first and watching on the demo account)*
- **C. Queue it, but only for a bounded window** — e.g. re-entry within N
  minutes counts, after that the setup is stale. Needs a number from you.

**ANSWER: A** (owner, 2026-09-01) — keep discarding. No code change; this is
current behaviour, recorded so it is a decision rather than an accident.

The reasoning that survives: price pushing toward the stop before entry is
evidence against the setup, and a channel's zone is a statement about a moment.
If this is ever revisited, C (queue for a bounded window) is the middle ground
and needs a number.

## A related setting you should know exists

**Entry Realignment** (`lk_entry_realignment`, currently **0 / off**) does a
third thing: on a breached zone it enters at market anyway and shifts the stop
and every target by the same distance, preserving the trade's geometry at the
new price.

```python
realigned_sl  = round(stop_loss + delta, 2)
realigned_tps = {n: round(v + delta, 2) for n, v in tps.items()}
```

Two caveats. It is off. And it lives only in the **limit-order** path
(`limit_order_signal.py`) — the signal above went through the **market**
auto-execute path, which has no realignment branch at all. So even switched
on, it would not have applied here.

That is arguably its own gap: the same situation is handled two different ways
depending on which path the signal took. Worth deciding alongside A/B/C above.

**ANSWER (should realignment exist on the market path too?): YES — when the
option is selected** (owner, 2026-09-01). Implemented.

### What was built

`Entry Realignment` now applies on the market auto-execute path as well as the
limit-order path. **It is still off by default**, so nothing changes for anyone
who has not switched it on — that is decision A above, untouched.

When it IS on and a zone is breached, the stop and every target move by the
breach distance, so the trade keeps the shape the channel sent, at a worse
price. On the signal that prompted this:

| | Sent | Entered at 4540.45 |
|---|---|---|
| Stop | 4544.00 | **4545.45** |
| TP1 | 4535.00 | **4536.45** |

5.00 of stop and 5.00 to TP1 — as specified. Entering flat would have left 3.55.

### The safety rule inside it

It refuses rather than realigns whenever the numbers would not be safe: not an
actual breach, exactly on the zone edge (which `price_in_entry_range` counts as
*in* the zone, and the two must not disagree about the same price), or a
realigned stop that would land on the wrong side of the entry. That last one is
not a wide stop — it is an immediate close, and no trade is better than that
trade.

A refusal falls through to the discard, so the worst case is exactly today's
behaviour.

### Verification

17 unit tests on the arithmetic, 4 end-to-end through the real pipeline, and 7
mutations all caught — including the setting being ignored, the stop or targets
not moving, the delta taken from the wrong edge, and a favourable move being
treated as a breach.

**It has not been run on a broker.** Add it to the demo session: switch the
setting on, wait for a breached signal, and check the stop lands where the
table above says.
