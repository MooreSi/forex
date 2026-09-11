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
