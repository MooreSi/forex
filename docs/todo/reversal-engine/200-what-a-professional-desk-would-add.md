# 200 - Beating the market with the Reversal Engine: what is missing, in order

**Status:** design note, nothing built. Written 2026-09-11 in answer to "how do
we beat the market with the reversal signal generator, the right EA template,
the app settings, and whatever a professional desk has that we do not."
**Money:** every section below can move money. Nothing here is authorised to be
switched on. Read [10-golden-rules](../../system/rules/10-golden-rules.md) first.

Everything asserted about this system was read out of the code and out of the
measurements already in `docs/todo/reversal-engine/` and
`docs/todo/data-inspect/003`. Where a claim is my judgement rather than a
measurement, it says so.

---

## 0. The one paragraph that matters

The engine is not bad at picking direction. It wins **59.4%** of executed
trades and has won roughly 60% every month since July. It loses money because
a win returns **0.642R** and a loss costs **1.161R**, which needs **64.4%** to
break even. Every feature proposed below is judged on one question: does it
move win size up, loss size down, or trade count down on the bad cohort. A
feature that only raises the hit rate makes this worse, because the usual way
to raise a hit rate is a nearer target, and a nearer target lowers the payoff.

Two arithmetic targets, both already stated in the README and both worth more
than any new signal source:

| change | break-even needed | result at today's 59.4% |
|---|---|---|
| today | 64.4% | losing |
| hold losses to 1.0R | 60.9% | still marginally losing |
| losses 1.0R and wins 1.0R | 50.0% | **+0.12R a trade** |

That is the whole game. A professional desk would not add a single new
indicator until those two lines were closed out.

---

## 1. Three defects in the current generator, in priority order

### 1.1 The payoff is inverted by construction

`signal_generator.py` places TPs at **fixed point offsets**
(`_TP_OFFSETS = [3,4,5,6,8,10,15,30]`) while the stop varies with level
quality (`_SL_DIST_BY_SCORE`: 7pt strong, 5pt medium, 4pt weak). So TP1 is
0.75R on a weak level and 0.43R on a strong one. **The better the level, the
worse the payoff.** The docstring is honest about this and argues the fix is a
narrower stop on strong levels rather than a wider target, because only 9.4%
of signals ever travel 1.0R.

That argument is right about the direction and incomplete about the method. A
desk would not pick either number by hand. It would fit both barriers to the
**conditional distribution of forward excursion** for that level type, session
and volatility bucket: choose the stop at a quantile of MAE for trades that
eventually win, and the target at a quantile of MFE. That is the triple
barrier method, and it needs excursion data, which is section 1.2.

### 1.2 We are waiting 20 days for data the broker already has

Items [020](020-losses-exceed-the-stop.md) and
[030](030-wins-are-cut-at-two-thirds-of-a-r.md) are both blocked waiting for
`mfe_pts` / `mae_pts` to accumulate forward at roughly 9 signals a day, which
puts them in early October. They do not need to be.

`bridge.get_ticks_range(from_ts, to_ts)` exists end to end today:
`mt5_bridge._get_ticks_range` -> `/ticks` -> `mt5_client` / `mt5_native` ->
`runtime.get_ticks_range`, bounded to a day per call, and
`services/backtest/engine.py` already consumes it. Every executed signal has
an open time, a close time, an entry, and a stop. **The excursion of all 745
historical executed signals can be reconstructed from broker tick history in
one offline pass**, subject only to the broker retaining ticks that far back
(check that first, it is one call).

This is the highest value single task on the whole list. It converts two
blocked items into two measured items, this week, at zero live-money risk,
and it is the input every other proposal below depends on.

Caveat worth stating before anyone runs it: a backfilled excursion measures
the path of a trade that was managed by the rules in force at the time. It
tells you where price went. It does not tell you what an unmanaged trade would
have done past its actual close, so cap the reconstruction at the real close
time and be explicit that MFE after an early exit is unobservable. For the
counterfactual you want section 5.3.

### 1.3 The ML gate is answering the wrong question

`re_ml` regresses R-multiple over the whole signal population and blocks below
0.0. `re_ml_meta.pkl` records `mean_r = -0.083` at every retrain. As
data-inspect/003 puts it, the model is correctly learning that its own signals
lose money, so as it improves it blocks more: 31% executed on 2026-09-02, 11%
on 2026-09-07. A gate that converges on "trade nothing" is not a filter, it is
a verdict on the generator.

Also structurally weak, and this is judgement rather than measurement:

- **Every version bump discards the fitted models.** v9 rebuilt from scratch
  on 2026-09-05, and 5 of its 38 features are the `_FEATURE_NEUTRAL` constant
  for 96% of training rows. Five constant inputs cannot help and can hurt
  through variance.
- There is no sign of **purged, embargoed cross validation**. Labels here are
  path dependent and overlapping in time (a 2 hour pending window, concurrent
  open signals, shared level cooldowns), which is the exact case where plain
  k-fold leaks and reports a model that does not exist.
- There is no **deflated Sharpe or backtest overfitting probability**, so
  there is no way to say whether v9 beating v8 on a sample is signal or the
  20th draw from the same urn.

The professional shape of this is **meta-labelling**: the level detector keeps
deciding direction, and a second, small, honestly validated classifier decides
only *act or do not act, and at what size*. Its label is not R, it is a binary
"did this trade clear its cost". That problem is learnable on 4,800 rows. A
continuous R regression on the same rows is not.

---

## 2. The EA template I would use, and why

### 2.1 What the current template cannot express

Item 030 found that **83% of executed signals never reach TP1**, yet 59% close
positive, so the profit is being taken by something other than the ladder, and
the suspect is the breakeven move. The split is 315 trades with BE never moved
at **+0.767R** against 126 BE-moved at **+0.333R**, and the file is correctly
cautious that BE-moved trades are a selected population.

### 2.2 Recommendation: a new template, not an edit of an existing one

Create **"Reversal ATR v1"**, single entry, and leave every existing template
untouched so the change is A/B observable rather than a silent retune.

Field by field, with reasoning. Pips here are EA pips: `PipsToPrice(p) = p *
10 * _Point`, so on XAUUSD 10 pips is 1.0 in price, which is 1 "point" in the
generator's own units. A 5.75 point mean stop is **57.5 pips**.

| field | value | why |
|---|---|---|
| `mode` | `single` | grid mode is refused by the backtest simulator and doubles the exposure question. Not while the payoff is unsolved. |
| `use_dynamic_atr` | `true` | this is the fix for 1.1. Stop and first target both scale with the same volatility measure, so R is constant across regimes instead of inverted. |
| `atr_period` | `14` | matches `ict_patterns.atr` so the app and the EA agree on the number. |
| `atr_sl_mult` | `1.2` starting value | to be replaced by the fitted MAE quantile from 1.2 as soon as it exists. Provisional. |
| `atr_tp1_mult` | `1.2` | deliberately equal to the stop multiple. A 1:1 first target at a 59.4% hit rate is profitable; the current 0.43R first target is not. |
| `partials` | `true` | |
| `tp1_pct` | `50` | half off at 1.0R, which is where the reach data says price actually gets to. |
| `tp2_pips` / `tp2_pct` | 2.0R equivalent / `50` | the runner. Only two rungs, because an 8 level ladder whose levels 2 to 8 fire on 7% of trades is decoration. |
| `close_full_on_last` | `true` | |
| `be_mode` | `entry_buffer` | |
| `be_buffer_pts` | `1.0` | |
| `be_trigger` | `1` | move to breakeven only **after TP1 has actually paid**, never before. This is the single most important line in the table: item 030's evidence points at a breakeven that arms too early and converts 0.767R winners into 0.333R scratches. Arming it after a booked partial cannot do that. |
| `trail_mode` | `step` | `staged` is explicitly refused by `template_simulator.py`, so a staged template cannot be backtested at all. Step can. |
| `trail_activation` | `12` (1.2R at the ATR multiple above) | |
| `trail_distance` | `12`, `trail_step` `3` | |
| `guard_pips` / `safety_cap_pips` | `10` / `10` | keep the defaults. These are what stop a breakeven modification being rejected, the failure that cost a full -$100 on ticket 1663956102. |
| `max_spread_pips` | `6.0` -> measure, then set | see 5.1. On gold at news this is routinely breached and a 6 pip spread against a 57 pip stop is 10% of R. |
| `late_guard_pips` | set it, non zero | this is the template-level twin of item [040](040-filter-the-instant-fills.md): sub 5 minute fills lose $2,142. A fill materially beyond the zone is the same adverse selection in a different coordinate. |
| `signal_rr_ratio` | `0.9` | refuses any signal whose own TP1:SL is below 0.9. Under today's generator that rejects the entire strong-level cohort, which is the point: it makes the inversion in 1.1 impossible to ship silently. |
| `equity_protect` / `basket_harvest_threshold` | leave `0` | portfolio level risk belongs in the risk governor, not in a per-channel template, and doubling it up makes attribution impossible. |
| `harvest_pips` | `0.0` | must stay 0. A positive value silently overrides the dollar threshold; that is the 2026-08-26 bug where a $30 harvest closed two trades at $1.40. |

**Do not ship this template without a demo session.** It changes where the
stop sits, where profit is taken, and when breakeven arms, which is three
money-touching changes in one object.

### 2.3 What the backtest cannot tell you about it

`template_simulator.py` refuses grid mode, resting entries, live ATR sizing,
account-wide harvest, and the `staged` and `fractal` trails. The template
above is deliberately inside what it supports **except** `use_dynamic_atr`.
Either teach the simulator ATR sizing (it already has bars, so this is small),
or backtest a fixed-pip approximation and accept that the live template will
differ in volatile regimes. I would teach the simulator, and say so plainly in
its docstring, because an unbacktested money change is the thing this repo's
rules exist to prevent.

---

## 3. App settings I would change today, without new code

None of these are authorised here; they are the list to take into a demo
session.

1. **Turn on and then measure item [040](040-filter-the-instant-fills.md)**,
   the instant fill filter. It is built, off by default, never demoed, and the
   cohort it removes lost $2,142. This is the cheapest money on the list.
2. **Item [050](050-revalidate-resting-orders.md) and
   [100](100-revalidating-every-waiting-order.md)**, revalidation of resting
   and waiting orders. Built, off, not demoed.
3. **Raise `_ML_BLOCK_THRESHOLD` off 0.0 only after section 1.3 is done.**
   Today the threshold is doing something real but for the wrong reason. Do
   not tune a number whose model is about to be replaced.
4. **Session gating.** Live executions by session: off 66.7% and +$57, asian
   59.3% and -$938, ny 56.2% and -$342. That is not a strong enough spread to
   switch a session off on its own, and the sample sizes differ by 7x, but it
   is strong enough to be a fitted feature rather than a hand rule. Do not
   hand-tune it; feed it to the meta-labeller.
5. **Expert Tunables to add**, following
   [60-adding-a-tunable](../../system/rules/60-adding-a-tunable.md), each
   defaulting byte-identical to today's constant: `_ML_BLOCK_THRESHOLD`,
   `PROXIMITY_THRESHOLD_PTS` (8.0), `_MAX_OPEN_SIGNALS` (6),
   `_LEVEL_COOLDOWN_S` (1800), `_SIGNAL_MAX_AGE_S` (7200),
   `_CONSEC_LOSS_LIMIT` (3). Every one of these is a behaviour constant a
   trader would want to move and currently cannot.

---

## 4. Entry accuracy: what would actually improve it

Ranked by expected value per unit of work, judgement informed by the measured
data above.

### 4.1 A liquidity map the engine does not currently have

`level_detector.py` produces Asia range, H1 swing highs and lows, round 5s and
10s, and congestion zones, plus the GD2 unicorn path (sweep, market structure
shift, FVG over breaker). That is a good ICT-flavoured map and it is missing
the levels most institutional intraday desks actually reference:

- **Previous day high, low, and close; previous week high and low.** These are
  the most reliably reacted-to intraday levels in gold and they are trivial to
  compute from the D1 candles the bridge already serves.
- **Daily open, weekly open, and the midpoint of the prior day's range.**
- **Session VWAP, and anchored VWAP from the prior swing or the session open**,
  with one and two standard deviation bands. VWAP is the single most widely
  used intraday reference price on any real desk, and this app has none.
- **Volume profile for the prior session: POC, value area high and low, and
  low volume nodes.** Gold CFD tick volume is a count, not a size, so this is
  a proxy, and a proxy POC is still far better than no POC. High volume nodes
  are where price returns; low volume nodes are where it travels fast, which
  is directly a statement about where a target should sit.
- **Initial balance** (first hour of the London and NY sessions) and its
  extension.

Each of these is a new `level_type` with its own score, and every one of them
becomes a feature the meta-labeller can weigh. This is the largest single
addition to *entry accuracy* available and none of it needs new data feeds.

### 4.2 Confirmation at entry, not just location

Today a signal fires when price is within `PROXIMITY_THRESHOLD_PTS` of a
ranked level. Location with no confirmation is why instant fills lose money:
price arriving fast at a level and being filled immediately is exactly the
case where the level is about to fail. Desks require a **trigger**, not just a
zone:

- rejection structure on a lower timeframe (M1/M5 candle close back inside the
  level after a wick through it)
- a measurable **deceleration** into the level: the ratio of the last N
  minutes' range to ATR falling, rather than rising
- for a sweep entry, the sweep must be **reclaimed** within a bounded number
  of bars, which `ict_patterns.detect_liquidity_sweep` is one step away from
  already

The app has M1 candles from the bridge, so all three are implementable with no
new inputs. Expected effect: fewer trades, better fills, directly attacking
the same cohort as item 040.

### 4.3 Order flow, honestly scoped

Professional gold desks read cumulative volume delta, footprint imbalance, and
absorption at the level. That is the real answer to "what do they have that we
do not". Two blunt caveats before anyone builds it:

1. **The bridge throws the data away.** `_get_ticks_range` returns only
   `{time, bid, ask}`; `copy_ticks_range` is called with `COPY_TICKS_ALL`, so
   `flags`, `last` and `volume` are available in the numpy array and dropped
   in the dict comprehension. Passing them through is a small, safe,
   non-money change.
2. **A retail gold CFD feed usually carries no trade side.** `TICK_FLAG_BUY`
   and `TICK_FLAG_SELL` exist in the MT5 tick structure, but on a spot CFD the
   broker typically publishes bid/ask ticks only, in which case true delta is
   unavailable and any CVD must be a tick-rule proxy (classify each tick by
   mid price direction). **Measure the flags on the live Vantage feed for one
   hour before designing anything on top of them.** Do not build a CVD feature
   on an assumption about a broker's tick stream.

Even with only bid/ask, three genuinely useful microstructure features fall
out: **tick arrival rate** (activity surge into a level), **spread dynamics**
(spread widening as price approaches is a liquidity withdrawal signal, and it
is also your cost), and **quote imbalance persistence**.

### 4.4 Cross-asset context at a resolution that works

`re_macro` has DXY momentum, US 10y level, a real-yield proxy via TIP, and
GVZ. The idea is right. The execution has the defect data-inspect/003 found:
the five series are neutral-filled for 96% of training rows, so they are
constants to the model. A desk would additionally watch the **gold/silver
ratio**, **SPX and VIX** for the risk-on/risk-off leg, and **positioning**
(CFTC Commitment of Traders, weekly, and gold ETF holdings, daily). None of
that is exotic; all of it is free.

The ordering point matters more than the list: **do not add a sixth macro
series until the five you have carry real values in the training set.** The
fix for that is backfill, from whatever historical source the series came
from, not another feature.

### 4.5 Regime: report it before classifying it again

`regime_score` is derived from ADX and ATR into trending/ranging/volatile. A
desk fits a regime model (a 2 to 4 state hidden Markov model or a clustering
on volatility, trend and autocorrelation) and then keeps **separate parameter
sets and separate performance accounting per regime**.

**Corrected 2026-09-11 on reading the code.** This codebase already has
THREE regime classifications -- `analytics/read_repo.get_regime_score`,
`test_signal/signal_indicators.detect_regime` and
`positions/core_auto_template.regime_from_candles`. A fourth would be a
genuine duplicate and the wrong first move. The thing that is actually
missing is the accounting, so regime shipped as an AXIS on
`reversal_engine/attribution.py` rather than as a new classifier: the
engine has enough closed trades to say whether it makes money on high-ATR
trend days and loses it in chop, and nothing in the app answered that.
Fitting a real regime model is worth doing after that table says regime
separates outcomes at all.

---

## 5. What a professional desk has that this system does not

Ordered by what I would build first. Each says whether the data already
exists.

### 5.1 Transaction cost analysis

**Data: exists.** `_get_tick_at` can recover the spread actually paid on any
past trade, and the trade history holds requested versus filled price.

There is no systematic record of **slippage per fill, spread paid at entry and
exit, or commission as a fraction of R**. Item 020 is trying to explain
0.53 points of leakage per loss without this. A desk measures cost on every
fill, attributes it to venue, session, and event proximity, and treats a
strategy's edge as net of measured cost, never gross. On a 57 pip stop a
6 pip spread crossed twice is over 20% of R. **This is very likely a large
part of the 0.642 versus 1.161 asymmetry and it is currently unmeasured.**

### 5.2 Meta-labelling with honest validation

**Data: exists.** See 1.3. Add purged and embargoed walk-forward, sample
weighting by label uniqueness (overlapping concurrent signals are not
independent observations), and a deflated performance statistic so that
"v10 beat v9" means something.

### 5.3 Counterfactual exit evaluation

**Data: exists via tick history.** For every closed trade, replay the tick
path and compute what a menu of exit policies would have returned: hard 1R,
2R, ATR trail, breakeven at 0.5R, no breakeven at all. This answers item 030
directly and settles the breakeven question without risking a live pound. It
is the single most useful piece of research infrastructure missing here.

### 5.4 Volatility targeting and a sizing policy

**Data: exists.** Sizing today is a fixed risk percent or fixed lot. A desk
sizes to a **volatility target**, scales down in drawdown, and caps
**correlated concurrent exposure**: six open XAUUSD signals in the same
direction is one position of six times the size, not six independent bets, and
`_MAX_OPEN_SIGNALS = 6` does not know that. Fractional Kelly (typically a
quarter to a half) on the meta-labeller's own probability output is the
standard shape, and it is only safe once 5.2 gives a calibrated probability.

### 5.5 Execution policy

**Data: partially exists.** Market versus limit is currently a strategy
property. A desk decides it per signal from expected adverse selection and
measured queue cost, posts passively when the level is expected to hold, and
crosses only when the signal is decaying. The instant fill finding is a symptom
of having no such policy.

### 5.6 Event and calendar discipline

**Data: partially exists.** `check_news_blackout` is binary. A desk tiers
events (FOMC, CPI, NFP, PPI, and gold-specific ones like central bank purchase
reports), widens or removes exposure by tier, and separately treats
**scheduled illiquidity**: the daily rollover window, the Sunday open gap,
month and quarter end, and option expiry. There is also an asymmetry worth
encoding: the danger is not only the event, it is the 20 minutes after, when
spreads are wide and stops are harvested.

### 5.7 Champion/challenger and shadow trading

**Data: exists.** Every new model or template should run in shadow against the
live one, recording what it would have done, for a pre-agreed number of trades
before it is allowed to touch money. Today a version bump goes live and the
evidence arrives afterwards, which is how v9 shipped on a Saturday and had its
worst Asian session the next trading day with nothing to compare it against.

### 5.8 Post-trade attribution

**Data: exists.** Per-cohort profit and loss, by level type, session, regime,
fill delay, spread bucket, and whether breakeven moved. Most of the analysis
in `docs/todo/data-inspect/003` was hand-written SQL on a Monday morning. A
desk has that as a standing panel that anyone can read before deciding
anything, and it is the difference between managing this engine and
periodically rediscovering it.

### 5.9 Capacity, correlation and multi-symbol

**Data: partially exists.** The bridge is hardcoded to one symbol
(`MT5_SYMBOL`, default XAUUSD) at the module level. Everything above is a
single-instrument bet on gold. A desk diversifies across correlated but
distinct instruments precisely because a single-symbol strategy's drawdown is
undiversifiable. This is the largest capability gap on the list and by far the
largest piece of work; it is listed last on purpose.

---

## 6. The order I would do it in

Nothing in phases 1 or 2 places or changes a trade.

**Phase 1, this week, no money at risk**
1. Backfill MFE and MAE for all executed signals from broker tick history (1.2).
2. Build the counterfactual exit replay on top of it (5.3).
3. Build transaction cost analysis from the existing tick and trade history (5.1).
4. Close out items 020 and 030 with the results.

**Phase 2, next, still no money at risk**
5. Fit the barriers (stop and target quantiles) from the excursion distribution.
6. Replace the R regression with a meta-labeller, purged walk-forward validated (5.2).
7. Add the missing levels: PDH/PDL, daily and weekly open, VWAP with bands, prior session volume profile, initial balance (4.1).
8. Add the entry trigger requirement (4.2).
9. Backfill the five macro series so they stop being constants (4.4).
10. Teach `template_simulator.py` ATR sizing.

**Phase 3, demo account only, one change at a time**
11. Turn on items 040, 050 and 100, one at a time, measured.
12. Ship the "Reversal ATR v1" template in shadow (5.7), then on the demo.
13. Sizing policy and correlated exposure cap (5.4).

**Phase 4, only if phases 1 to 3 produce a positive expectancy**
14. Order flow, if and only if the feed measurement in 4.3 says the data exists.
15. Multi-symbol.

---

## 7. What needs the owner or a demo session

- Any change to stop placement, target placement, or the breakeven trigger,
  which is the entire section 2.
- Turning on items 040, 050, 100 or the new template on any account.
- The sizing policy in 5.4.
- A judgement I cannot make: **whether this engine should keep emulating the
  reference channels at all.** The correlation machinery exists to benchmark
  against Gold Diggers, and the generator's geometry is reverse engineered
  from their messages. Their geometry is what produces the 0.43R first target.
  Fitting barriers to our own excursion data means the engine stops resembling
  them. That is a trading policy decision, not an engineering one, and it
  belongs in `docs/simon-handover/`.
