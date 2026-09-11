# 210 -- What was built on 2026-09-11, and what is still waiting on you

Everything in [200](200-what-a-professional-desk-would-add.md) was built in
one session, plus the defects it named. This is the inventory, the switches,
and the honest list of what is not done.

**Nothing in here changes what the app trades.** Every new decision is
behind a setting that defaults to off, and every default is byte-identical
to the behaviour it replaces. The full suite, all four gates, the coverage
ratchet and the boot smoke were green when it was written.

---

## The defects

| # | defect | what shipped | on? |
|---|---|---|---|
| 1.1 | fixed TP offsets against a level-score stop: TP1 is 0.43R on a strong level and 0.75R on a weak one | `signal_generator.atr_barriers` -- stop at `ATR x stop_mult`, ladder rescaled so TP1 lands at `ATR x tp1_mult`, relative spacing preserved | `re_atr_barriers_enabled`, **off** |
| 1.2 | items 020 and 030 blocked waiting for excursion to accumulate forward | `excursion_backfill` reconstructs it from broker tick history, for every closed executed signal | on demand, writes two columns |
| 1.3 | the ML gate regresses R over a population whose mean R is negative, so it converges on "trade nothing" | `meta_label.MetaLabeller` -- binary "did this clear its cost", purged and embargoed folds, uniqueness weighting, refuses to arm below 0.55 AUC out of sample | `meta_label_gate_enabled`, **off** |

## The capability gaps

| § | gap | module | reachable from |
|---|---|---|---|
| 4.1 | no previous-day/week levels, no VWAP, no volume profile, no initial balance | `market/liquidity_map`, `market/vwap`, `market/volume_profile` | `liquidity_map_levels_enabled`, **off** |
| 4.2 | a signal fires on proximity with no confirmation | `market/entry_trigger` | `entry_trigger_enabled`, **off** |
| 4.3 | the bridge threw away `flags`/`last`/`volume`; no order-flow measurement | bridge passthrough + `market/order_flow` | the study's feed probe |
| 4.4 | five macro features are a constant for 96% of training rows | `macro_backfill` | controller, **dry run by default** |
| 4.5 | no per-regime accounting | `attribution`'s extra-axis hook | the study |
| 5.1 | execution cost is a constant, never measured | `broker/tca` + `tca_repo`, table `execution_quality` | the study |
| 5.2 | no purging, no embargo, no multiple-testing correction | `market/validation` | `meta_label` |
| 5.3 | no counterfactual exit evaluation | `market/exit_replay`, `market/barrier_fit` | the study |
| 5.4 | sizing knows nothing about volatility, drawdown or correlated exposure | `risk/sizing_policy` | `vol_target_sizing_enabled`, `correlated_exposure_cap_lots`, **both off and NOT wired to the order path -- see below** |
| 5.6 | binary news blackout; no clock-driven illiquidity | `risk/event_tiers`, `risk/session_liquidity` | `event_tier_gate_enabled`, `session_liquidity_gate_enabled`, **off** |
| 5.7 | a version bump goes live and the evidence arrives afterwards | `reversal_engine/shadow` -- champion and four challengers, recorded per fill attempt | always records; changes nothing |
| 5.8 | the cohort analysis is hand-written SQL on a Monday morning | `reversal_engine/attribution` | the study, Reversal panel |
| 5.9 | single-instrument by construction | `market/correlation` -- cross-asset correlation and a correlation-aware exposure number | the study |

## The EA template

`Reversal ATR v1`, in `broker/ea_template_presets.py`, created by the **Add
Built-in** button on Trading > EA Templates. It is **assigned to no
channel** and trades nothing until somebody selects it.

Two supporting changes made it real rather than notional:

- **`atr_ladder_scale`** (migration 39, off by default). `use_dynamic_atr`
  sized the stop and TP1 only, so a volatile day moved those two and left
  TP2 where it was. This rescales the whole anchor ladder around TP1 and
  keeps its spacing.
- **The backtest can now evaluate it.** `template_simulator` refused
  `use_dynamic_atr` outright; the bar walk now takes the ATR the engine
  already computes at the fill. The tick walk still refuses, because a tick
  series has no candles to derive one from.

## The one thing deliberately left unwired

**`sizing_policy` is built, tested and NOT connected to the order path.**

Position sizing is on the short list of things this repo says to stop and
ask about, and "the user said build it" is not sign-off for the
money-touching half. The module is pure and its composed default returns
the lot size it was given, unchanged. Connecting it is one call at the
sizing site, and it wants a demo session and someone watching.

## How to turn any of it on

**Trading > Strategy > Reversal Engine Capabilities**, then Save
Capabilities. The card sits beside the other behaviour gates because these
are tier-2 trading behaviour, not calibration constants
([60-adding-a-tunable](../../system/rules/60-adding-a-tunable.md)).

The switches shipped on 2026-09-11 with no UI at all, which meant the only
way to reach them was editing `vantage_risk_settings` by hand. That was an
omission, not a design choice; the card and
`tests/frontend/test_capability_switches_have_controls.py` (which fails if a
migration adds a switch the form forgets) landed the same day.

Two switches behave differently from the rest and the card says so:

- **Ask the meta-labeller** does nothing until the Research study has costed
  a few hundred trades. The model refuses to arm until it can beat a coin
  out of sample, and an unarmed model blocks nothing.
- **Scale size by volatility and drawdown** records the intent and changes
  no lot size, because `sizing_policy` is deliberately not wired to the
  order path yet.

## What to do next, in order

Nothing in steps 1 to 3 risks a pound.

1. **Run the study** (Reversal panel > Research > Run study). It probes what
   the broker's tick history actually reaches back to, reconstructs
   excursion for every closed trade, prices every fill, and prints the
   attribution table, the fitted barriers and the exit-policy sweep.
2. **Read the barrier fit.** If it refuses on sample size, that is the
   answer: it needs more backfilled trades, and the probe will say whether
   the broker can supply them.
3. **Read the breakeven line in the sweep.** `tools/exit_policy_lab.py`
   found a penalty in 8 of 8 configurations on the main trading path. If
   the reversal engine's own trades agree, item 030 is settled.
4. **Then a demo session**, one switch at a time, in this order: items 040
   / 050 / 100 (already built, still never demoed), then
   `re_atr_barriers_enabled` with the fitted multiples, then the template
   in shadow, then sizing.

## What was NOT built, and why

- **Multi-symbol trading.** The bridge binds one symbol at module level, and
  so do the EA and the trade schema. Multi-symbol market DATA is wired
  (`get_candles_for_symbol` was already there) and `market/correlation` uses
  it; placing an order on a second instrument is a separate piece of work
  measured in sessions.
- **A real regime model.** Three regime classifications already exist in
  this codebase. A fourth is a duplicate; the accounting was the gap, and
  that shipped.
- **Refitting `score_level`'s type weights.** They rank how well a level
  predicts the reference channel's behaviour rather than whether the trade
  makes money. Changing them changes which signals fire, and the evidence to
  change them correctly is the attribution table that has just started
  collecting. See [simon-handover/029](../../simon-handover/029-the-engine-no-longer-copies-gold-diggers.md).

---

## Verification log

`python -m tools.checks all`, 2026-09-11, on macOS, against the tree this
commit contains:

```
Running 11 check(s)

  structure gates        ok   (2.4s)
  import contracts       ok   (2.0s)
  runtime facade         ok   (0.0s)
  orphan modules         ok   (0.9s)
  undefined names        ok   (1.2s)
  unawaited coroutines   ok   (1.0s)
  late binding           ok   (0.6s)
  boot smoke             ok   (3.0s)
  doc links              ok   (0.1s)
  test suite             ok   (374.2s)
  coverage ratchet       ok   (0.1s)

All checks passed.
```

333 of those tests are new and belong to this change.

**What this does NOT verify.** Every switch listed above is off, so the
suite proves the new code is correct and that turning it OFF changes
nothing. It proves nothing about the behaviour of any of them turned ON.
That is what the demo session is for, and it is why they ship off.

---

## First live run, 2026-09-11 15:26, demo account 26004592

The app was restarted onto commit `2c7768e` and the study run from the
panel. Migrations 39, 40 and 41 applied to the database actually in use
(`forex_trader_demo_26004592.db`, now at schema version 41) and every new
switch came up off.

`forex_trader_demo.db` (account 25470480) is at version 35 and NOT migrated.
It has not been written to since 2026-09-09 -- it is the previous account's
database and is no longer in use. Worth knowing before anyone queries it and
reads the numbers as current.

### What the study found

**The broker keeps 30 days of ticks, not 90.** `{1: 36797, 7: 27641,
30: 25329, 90: 0, 180: 0}`. Excursion can be reconstructed a month back and
no further, so the backfill is a one-off catch-up plus whatever the live
sampler collects from here.

**469 excursions reconstructed in about 90 seconds**, 31 with no tick
coverage, zero failures. Coverage went from 102 to 571 of 785 closed live
trades. Items 020 and 030 are no longer blocked on data.

**The feed carries no trade side.** "quote-only feed: no trade side, so
delta can only ever be a tick-rule proxy on this instrument". That is the
measurement section 4.3 insisted on before building anything on delta, and
the answer is: do not build measured delta on this broker.

**Measured round-trip cost: 0.372R**, from 289 costed fills -- mean 0.219
points of spread and 0.438 points of slippage against a mean 3.71 point
stop. **Read the slippage figure carefully**: the reference price is the
middle of the signal's own entry zone, so it measures the distance between
where the signal said it wanted in and where it actually got in. That is a
real cost and it is not broker slippage. Separating the two needs the
decision-time tick, which is a small follow-up.

**The fitted barriers are a diagnosis, not a recommendation.** Stop 18.82
points (2.5x ATR), target 4.85 (0.6x ATR), implied R:R 0.258 from 351
winners. Read plainly: on this population the trades that eventually win
frequently go a long way against first and then barely travel in favour.
Nobody should set a 2.5x ATR stop off this; it says the entries are the
problem, not the exit geometry.

**Every exit configuration's 95% interval straddles zero** on the 60-path
sample. The best cell (stop 2 / target 12) is +0.481R [-0.364, +1.333],
holding sign across both chronological halves. The gradient toward a
tighter stop and a wider target is the same one `tools/exit_policy_lab.py`
found independently in July, which is worth something; the intervals say
raise the sample before acting.

**Item 030's suspect is cleared.** The replay prices the breakeven move at
+0.036R, +0.027R and -0.007R across three stop/target pairs -- roughly free,
not the large penalty the naive split implied. The attribution table shows
exactly why the naive reading was wrong: BE-moved trades are 126 rows at a
**100% win rate**, because a trade only reaches breakeven by going into
profit first. The replay controls for that selection. **The breakeven move
is not what is costing the engine money.**

**`score_level`'s weights are contradicted by outcome.** `round_5` is
scored highest at 0.78 and is the worst cohort on the book: 210 trades,
-0.157R, -$1,322. `unicorn` is the best at +0.559R and +$625 on 18 trades.
This is the evidence `simon-handover/029` said would be needed to refit
those weights.

**Item 040 confirmed on a much larger sample.** Fills under five minutes:
453 trades, -$1,950. Every other delay bucket is near flat.

**Asian session is the worst**: 309 trades, -$1,043.

### A defect the run found in this build

The macro repair reported "0 vectors to repair", which was wrong.
`needs_backfill` skipped any vector shorter than the current 38-feature
schema, and **3,359 of 5,000 stored vectors are 33-wide** against 698 at
full width. It was therefore a no-op on 96% of exactly the population
`data-inspect/003` identified.

Fixed: a short vector is now widened with each missing feature's documented
neutral -- through `_feature_schema.pad_to_schema`, the same function
training uses, extracted verbatim so a repaired row and an in-memory padded
one cannot come to mean different things -- and then its macro block is
filled from history. It now reports **4,302 vectors to repair**. Still dry
run by default: applying it changes what the ML gate learns.

The test that pinned the old behaviour was rewritten rather than deleted,
and says why the original expectation was wrong.

---

## Housekeeping, 2026-09-11 16:00

The stale databases were cleared at the owner's request:
`forex_trader.db` (empty since August) and `forex_trader_live.db` (never held
a trade) deleted, the pre-migration backups deleted, and the 25470480
database moved to `data/archive/` rather than destroyed -- it holds 1,398
trades from 21 July to 3 September and several docs cite its numbers.

**That archive move broke the next boot**, because the file it moved was
also the DEFAULT database path, which `account_registry` falls back to on
every startup before the EA has said which account it is. The app created a
fresh empty database and ran on it for about a minute. Verified inert: zero
trades, zero signals, zero templates, every live-execution flag at its
schema default of off, and no positions at the broker.

Fixed by consolidating onto one file -- the live account's database now IS
the default path, and `accounts.json` maps 26004592 to it -- so the fallback
and the resolved path can no longer diverge. Verified after restart: schema
43, 291 trades, 23 templates, `re_live_execution` back at 1, the 289
execution-cost rows intact, and every capability switch still off.

The full write-up is in
[docs/system/domains/data](../../system/domains/data/README.md); it also
explains why the archived database was six migrations behind, which had been
an open puzzle.

Four older `.bak-*` files remain in the data directory, including one from
the in-progress ledger repair. Those are not mine to remove.

---

## The macro repair, applied 2026-09-11 16:16

The owner authorised it. 4,288 of 5,000 stored training vectors repaired;
712 already carried real values. Every stored vector is now 38 wide and
none carries the macro constants.

### It did not work the first time, and the dry run is why that was cheap

The first dry pass reported **4,288 rows with "no data"** and wrote nothing,
which reads exactly like Yahoo having no history for the period. It was not:
`fetch_history` did `row["Close"]` over `df.iterrows()`, and yfinance 1.7
returns **MultiIndex columns** -- `('Close', '^VIX')` -- even for a single
ticker, so that expression yields a one-element Series rather than a float.
`float()` on it raised, the broad `except` swallowed it, and every symbol
came back empty.

A guessed dataframe shape. The seam is now `_closes_from_frame`, tested
against both column layouts, against a NaN row and against a frame with no
Close at all. Second dry pass: 4,288 to repair, **zero** without data.

### What the constants were actually saying

They were not merely uninformative. They were systematically wrong about
the regime the engine was trading in:

| feature | neutral it held | real range in the training set |
|---|---|---|
| `gvz_level` | 0.425 (GVZ 17) | 0.581 to 0.736 (GVZ 23 to 29) |
| `vix_level` | 0.500 (VIX 20) | 0.350 to 0.516 (VIX 14 to 21) |
| `us10y_level` | 0.750 (4.50%) | 0.769 to 0.825 (4.61% to 4.95%) |
| `dxy_momentum` | 0.000 | -1.000 to +0.509, 545 distinct values |
| `tip_momentum` | 0.000 | -1.000 to +1.000, 196 distinct values |

Gold volatility is the clearest: every historical row told the model GVZ
was 17 through a period when it never once dropped below 23. The model was
not just missing the macro picture, it was being given a false one.

### When it takes effect, and what to watch

The model persisted before the repair is still in memory and still scoring
signals. A batch retrain fires every 5 closed signals
(`_RETRAIN_EVERY = 5`), so the repaired data reaches the live gate within
an hour or two of trading, not on restart.

**Watch the block rate.** `_ML_BLOCK_THRESHOLD` is 0.0 and the gate was
already refusing most signals (11% executed on 2026-09-07). If five inputs
going from a false constant to real values changes what it refuses, that
shows up as a step change in the `ml_skipped` count, and the direction is
not predictable from here.

The pre-repair database is at
`reversal_engine.db.pre-macro-repair-20260911-161641` if it needs undoing.
