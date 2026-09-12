# 047 — `detect_equal_levels` cannot see two highs that are exactly equal

**Status:** found 2026-09-12 while writing the first tests for the ICT pattern
chain. **Not fixed** — the one-line fix changes which liquidity pools form and
how many touches each records, on the only engine in this app with live
execution turned on.
**Touches money:** yes, indirectly but on the live path. Pools feed
`detect_liquidity_sweep`, which feeds `find_unicorn_setup`, which becomes a
real order.
**Severity:** it silently drops the strongest version of the exact signal it
exists to find.

## The defect

`ict_patterns.detect_equal_levels` describes itself as:

> *"Equal-highs / equal-lows liquidity pools … A pool is 2+ swing extremes
> within `tolerance_pts` of each other; more touches = a bigger
> resting-liquidity magnet and a higher-quality sweep target."*

It builds its candidates like this:

```python
highs = sorted(set(round(_hi(c), 1) for c in recent), reverse=True)
lows  = sorted(set(round(_lo(c), 1) for c in recent))
```

**`set()`.** Two candles whose highs round to the same 0.1 collapse to a single
value, the cluster has one member, and `len(cl_) >= min_touches` (2) drops it.

So:

| two highs | pool? |
|---|---|
| 110.0 and 110.4 | **yes** — price 110.2, touches 2 |
| 110.0 and 110.0 | **no** — nothing at all |

A textbook double top — the cleanest equal high there is, and the strongest
resting-liquidity magnet on the chart — is the one shape this detector cannot
see. Nudge one of the two candles by a single tick and it appears.

Both tests are in
`tests/reversal_engine/test_ict_pattern_chain.py::TestTheDefectInEqualLevels`,
which pins today's behaviour deliberately so that fixing it is a visible,
intentional change rather than a silent one.

## How much it costs is not known from here

XAUUSD M15 highs rounded to 0.1 repeat often enough in a quiet session that
this is not a theoretical case, but how often it costs a pool depends on live
data. What can be said: when it happens, the engine loses the pool entirely —
not a quality score, the whole level — and with it any sweep of that level and
any Unicorn setup that would have followed.

## The fix, and why it is not applied here

Drop the `set()`:

```python
highs = sorted((round(_hi(c), 1) for c in recent), reverse=True)
lows  = sorted(round(_lo(c), 1) for c in recent)
```

That is the whole change, and it is not as small as it looks:

1. **Every repeated extreme now counts as a touch.** A flat range where twenty
   candles share a high becomes `touches: 20` rather than nothing. Touch count
   is used as a quality signal, so the scale of that number changes meaning
   across the whole system.
2. **Clusters chain.** `_cluster` compares each value to the last one added, so
   a dense run of near-equal values can walk a cluster wider than
   `tolerance_pts`. More values in the list makes that more likely, not less.
3. It changes which pools exist, on the engine that places real orders.

So it wants measuring before it is applied — count, over recorded `re_levels`
or a candle replay, how many pools appear and how the touch distribution moves.
That is an hour of analysis and then a demo session, not an unattended edit.

## Related

* `tests/reversal_engine/test_ict_pattern_chain.py` — the chain's first tests,
  written in the same pass (21 cases, seven mutants killed).
* `docs/system/domains/engines/README.md` — the Reversal Engine's section.
