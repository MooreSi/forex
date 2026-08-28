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

**ANSWER:**

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

**ANSWER (should realignment exist on the market path too?):**
