# 060 — The breakout engine's H4 bias has always been "neutral"

**Status: the starvation is FIXED. The gate it was hiding is still off and
is yours to decide** (2026-09-16).

Found 2026-09-16 while investigating the breakout engine's performance.

## The evidence

```sql
SELECT htf_bias, h4_bias, COUNT(*) FROM bo_signals
WHERE outcome IN ('win','loss') GROUP BY htf_bias, h4_bias;
```

| htf_bias | h4_bias | n |
|---|---|---|
| bullish | neutral | 64 |
| bearish | neutral | 53 |
| neutral | neutral | 5 |

**122 of 122.** `h4_bias` has never once been anything but `neutral`.

## The cause

[`breakout_signal_service.py:216`](../../../backend/src/services/breakout_signal/breakout_signal_service.py):

```python
h4_candles = await self._bridge.get_candles("H4", 40)
```

[`market/indicators.py:21`](../../../backend/src/services/market/indicators.py):

```python
def compute_h4_bias(h4_candles):
    if len(h4_candles) < 52:
        return "neutral"
    ...  # EMA20/50 needs 52 for warmup
```

40 < 52, so the function returns its neutral fallback every time and has
never evaluated a single EMA. `compute_htf_bias` on H1 is fed enough candles,
which is why `htf_bias` varies and `h4_bias` does not.

## What it silently disabled

**A gate that has never rejected anything.**
[`signal_generator.py`](../../../backend/src/services/breakout_signal/signal_generator.py),
four sites:

```python
(not dual_bias or h4_bias in ("bullish", "neutral"))
```

`neutral` is in both the bullish and the bearish allow-list, so with
`dual_bias` on the clause is always true. The dual-bias filter has been
switched on and doing nothing.

**An ML feature that is a constant.** `ml_engine.py:214`,
`h4_score = _bias_score(h4_bias)` — the same value on all 4,894 rows,
carrying zero information. Same fault the Reversal Engine's `macro_backfill`
exists to repair, in a different engine.

## Why the fix is not just `40 -> 56`

Raising the count turns a dead gate into a live one. Every signal that fires
today under `dual_bias` passed a clause that was vacuous; some fraction of
them will stop firing. That is a change to what the engine trades, so it
needs the owner and a demo session, and it wants measuring first:

* Backfill `h4_bias` on the stored rows from historical H4 candles (the
  bridge serves them; `excursion_backfill` is the precedent) and re-run the
  attribution to see how many past signals the live gate would have blocked
  and what they earned.
* Only then decide whether `dual_bias` should be on.
* The ML model needs a retrain after any backfill, and `ml_handover` rules
  apply.

Belongs with 059: both are the same class of fault, a number computed from
one thing and applied to another.


---

## Fixed 2026-09-16, and what was deliberately left off

**The indicator is fed.** `H4_BIAS_MIN_CANDLES = 52` now lives beside
`compute_h4_bias` in `market/indicators.py`, and all three windows derive from
it instead of restating a number:

| site | was | now |
|---|---|---|
| `breakout_signal_service` | `get_candles("H4", 40)` | `_H4_CANDLES` = warmup + 8 |
| `breakout_signal_live_execute` (fill-time re-check) | `get_candles("H4", 40)` | warmup + 8 |
| `backtest` slice | `h4[hi4 - 40:hi4]` | `hi4 - (warmup + 8)` |

The backtest mattered as much as the live path: every adaptive-parameter
tuning run this engine has ever been fitted on ALSO saw a permanently neutral
H4, so fixing the engine and leaving the backtest starved would have kept the
evidence wrong while the code was right.

**`require_dual_bias` default 1.0 -> 0.0.** This keeps behaviour rather than
changing it, which is the point. The setting has read "strict" since it was
written and has never rejected a signal, because `neutral` is in the
allow-list for both directions. Repairing the feed without touching it would
have armed a filter nobody has ever seen work, silently, in the same commit.
The default now states what the engine has actually been doing. **Turning it
back to 1.0 is the open decision**, and it wants the backfill and attribution
above first, then a demo session.

**What could NOT be held still.** `ml_engine`'s `dual_bias` feature is
computed from `h4_bias` directly and does not consult `require_dual_bias`. It
has been a constant across all 4,894 rows and will now vary, so the model's
output will shift at its next retrain and the ML gate will block a different
set of signals. That is the point of the repair and it cannot be switched
off, but it is a live behaviour change on a demo account and wants watching.
`ml_handover` rules apply to the retrain.

**Pinned by** `tests/breakout_signal/test_h4_bias_is_actually_computed.py`:
the indicator reads bullish and bearish once fed, every module that calls
`compute_h4_bias` is AST-scanned for a starved fetch, the resolved window
constant is checked (a literal scan alone missed a mutant that set
`_H4_CANDLES = 40`), and the dormant gate cannot be armed without failing a
test. Five mutants, four killed; the fifth is an equivalent mutant, confirmed
by removing both redundant guards and watching the test fail.


---

## Excursion measurement added 2026-09-16

The other half of "why does this engine lose". `bo_signals` carried no
`mfe_pts`/`mae_pts`, so the breakout engine has never had a reach
distribution and its `tp1_mult` of 1.0 has been a guess for its whole life --
`rr_tp1` is 1.0 on all 122 closed signals, and at the realised payoff of 1.30
that needs a 43.5% win rate against an actual 36.1%.

Shipped, all read-only measurement, placing nothing:

* `breakout_signal/measure_repo.py` -- the three filters that decide whether
  the numbers can be trusted (executed only, closed only, never overwrite),
  in their own module because adding them to `breakout_signal_repo.py` put it
  at 806 lines, over the ceiling. The reversal engine already keeps this
  concern in a `measure_repo.py`; two engines, one shape.
* `breakout_signal/excursion_backfill.py` -- reconstructs MFE/MAE from broker
  tick history through the same `market/price_path` the reversal engine uses,
  so the two engines' numbers mean the same thing.
* `breakout_signal/excursion_sweep.py` -- runs it nightly at 22:00 London on
  the timer `research_loop` already owns, with its own `bo_excursion_last`
  date key. Deliberately not a button: the reversal engine's study was
  button-only and went four days stale, and the same gap here would be worse
  because there is no history to go stale from.

**What this does NOT do is change a target.** It builds the evidence base for
choosing one. Nothing about `tp1_mult` is settled until the backfill has run
and `barrier_fit` has something to fit on.

For reference, the reversal engine's reach over 793 stored excursions, which
is the shape of answer to expect here:

```
 0.25R: 58.0%   1.0R: 41.5%   2.0R: 24.8%   3.0R: 14.9%
median reach 0.58R
```

Only a quarter of those trades ever touch 2R. If the breakout engine reads
similarly then RAISING its target is the wrong move and the lever is loss
size -- but that is a guess until measured, which is the entire point of
shipping this rather than a number.

Twelve mutants across the backfill, the repo filters and the sweep. Two
survived first time and both were real gaps, now closed: the UPDATE's
`AND mfe_pts IS NULL` overwrite guard (every test asserted which rows get
PICKED, none on what a second write does) and the observations query's
`live_exec_status='executed'` filter (every test created executed signals
only, so nothing could see it).
