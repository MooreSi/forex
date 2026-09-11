# 029 -- The reversal engine no longer has to resemble Gold Diggers

**Status:** **ANSWERED 2026-09-11 by the owner.** Acted on the same day; see
*What was built* below.
**Money:** yes. It changes where the stop sits and where profit is taken.
**Raised:** 2026-09-11, as section 7 of
[docs/todo/reversal-engine/200](../todo/reversal-engine/200-what-a-professional-desk-would-add.md).

## The question that was put

The reversal engine's geometry is reverse engineered from a Telegram
channel. `signal_generator._TP_OFFSETS` is a fixed list of point distances
taken from that channel's spacing, and `_SL_DIST_BY_SCORE` varies the stop
4-7 points with level quality. The consequence, stated plainly in the
generator's own docstring: TP1 is 0.75R on a weak level and 0.43R on a
strong one. **The better the level, the worse the payoff.**

`score_level`'s type weights are calibrated the same way -- against how often
the reference channel fired near a level, not against whether the trade made
money.

Fitting the barriers to our own excursion data means the engine stops
resembling them. That is a trading-policy decision, not an engineering one,
so it was put to the owner rather than assumed.

## The answer

> "it doesn't need to resemble gold diggers anymore, it now needs to develop
> itself into a world class signal generator/trade"

## What that settles

1. **Barriers are fitted to this engine's own excursion distribution**, not
   copied. The stop is a quantile of what winners actually survive; the
   target a quantile of where they actually reach.
2. **The correlation machinery becomes a benchmark, not an objective.**
   `reversal_engine_correlate.py` keeps measuring lead time against the
   channels. It is now a comparison, not a target.
3. **`pro_likeness` stays as a feature and stops being a goal.** "Would a
   reference channel fire here" is still information about the moment. It is
   no longer what good looks like.
4. **`score_level`'s weights are now on notice.** They rank how well a level
   predicts the channel's behaviour. What they should rank is whether the
   trade makes money, and `attribution.py`'s per-level-type table is the
   evidence that will settle it. They were NOT changed on 2026-09-11 --
   changing them changes which signals fire, and the evidence does not exist
   yet.

## What was built on the strength of it

All of it is **off by default** and none of it has been demoed:

- `signal_generator.atr_barriers` -- stop at `ATR x stop_mult`, ladder
  rescaled so TP1 lands at `ATR x tp1_mult`, which makes R constant instead
  of varying with level score. The ladder's relative SHAPE is preserved,
  because the reach data behind it (median 0.43R, 9.4% reaching 1.0R) was
  measured on this instrument and is the one part of the borrowed geometry
  that says something real.
- `market/barrier_fit.py` -- fits those multiples from real excursion, and
  refuses to fit on a sample too small to act on.
- Risk setting `re_atr_barriers_enabled`, default 0.

## What still needs you

**A demo session to turn it on.** The switch changes where the stop sits on
a live trade. The plan is one change at a time, measured:

1. `re_atr_barriers_enabled` with the fitted multiples, once
   `market/barrier_fit` has enough excursion to produce them.
2. The `Reversal ATR v1` EA template, in shadow first.
3. The remaining gates (entry trigger, liquidity windows, meta-labeller),
   one at a time.

**And one thing to decide later, not now:** whether `score_level`'s type
weights should be refitted against outcome once the attribution table has
enough rows. That is the same class of decision as this one.
