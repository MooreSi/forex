# 003 — Why the Reversal Engine got worse

**Asked by the owner, 2026-09-08:** why is it performing so badly recently, is
the ML still improving, did the ML change when the demo account changed, and
what happened to the overnight Asian-session profit.

**Method:** read-only queries against the live data on the Mac —
`reversal_engine.db` (4,794 signals), `forex_trader_demo.db` (1,524 closed
trades), `re_ml_meta.pkl`, and `accounts.json`. No writes.

**Answer in one line:** three separate things, and only one of them is recent.

---

## 1. The account change did NOT affect the ML. Confidently no.

`accounts.json` shows two demo databases:

```
25470480  -> forex_trader_demo.db          21.7 MB, 1,524 trades, live today
26004592  -> forex_trader_demo_26004592.db  380 KB,     0 trades
```

**The new account has never traded.** It was created 2026-09-03, seeded with
the shared tables, and holds no trades at all; the original database is the one
still being written to this morning.

The reversal engine is unaffected either way: its history lives in
`reversal_engine.db`, a single file that is **not** split per account. It was
never at risk from the split.

Worth noting separately: `account_registry.SHARED_TABLES` does not copy any
`re_*` table, so a new account genuinely used for trading would start with the
engine's config and history absent. That has not bitten yet because the second
account was never traded.

## 2. It has been losing since July. This is not recent.

Every closed signal, by month:

| month | n | win % | net |
|---|---|---|---|
| 2026-07 | 741 | 58.4 | **-$2,820** |
| 2026-08 | 3,232 | 61.1 | **-$13,408** |
| 2026-09 | 816 | 59.6 | **-$2,233** |

The win rate is stable around 60%. **The problem has never been signal
selection, it is payoff.** `ml_engine.py` measured this directly: losses
average -1.22R (worst -5.75R, stops slipping well past `sl_dist`), wins +0.39R
— a true payoff of 0.32:1. A 60% win rate at 0.32:1 loses money by
construction.

Live executions only, by session (744 executed):

| session | n | win % | net |
|---|---|---|---|
| asian | 302 | 59.3 | -$938 |
| london | 109 | 57.8 | -$611 |
| overlap | 186 | 60.8 | -$359 |
| ny | 105 | 56.2 | -$342 |
| off | 42 | 66.7 | +$57 |

## 3. What DID change recently, and it is two things at once

### (a) The ML model was thrown away on 2026-09-05

`ml_engine.py` is at `re_ml_v9`, shipped 2026-09-05 (`docs/todo/001`), and
every version bump since v3 **discards the fitted models and retrains from
scratch**. `re_ml_meta.pkl`'s `train_history` has 20 entries and the oldest is
**2026-09-07 09:27** — the model has no memory before Monday morning.

v9 also widened the feature vector from 33 to 38, adding the five macro series.
Measured on the stored vectors:

```
to 2026-09-06   33 features
2026-09-07      33 and 38 (the changeover, mid-day)
2026-09-08      38 features
```

Older rows are back-filled with `_FEATURE_NEUTRAL`, so of ~4,050 training rows
only ~175 carry real macro values. **Five of the model's 38 inputs are a
constant for 96% of what it learns from.**

### (b) The gate is now blocking three times as much

`_ML_BLOCK_THRESHOLD = 0.0` — live execution is blocked when predicted
R-multiple is below zero.

| day | signals | executed | ml_skipped |
|---|---|---|---|
| 2026-09-02 | 147 | 46 (31%) | 36 |
| 2026-09-03 | 165 | 43 (26%) | 45 |
| 2026-09-07 | 132 | **15 (11%)** | **58** |

And the Asian session, executed, which is the thing the owner actually watches:

| day | n | win % | net |
|---|---|---|---|
| 2026-09-01 | 12 | 75.0 | **+$215** |
| 2026-09-02 | 29 | 58.6 | **+$110** |
| 2026-09-03 | 17 | 70.6 | **+$177** |
| 2026-09-04 | 15 | 53.3 | -$78 |
| 2026-09-07 | 12 | **25.0** | **-$324** |
| 2026-09-08 | 8 | 50.0 | -$77 |

2026-09-05 was a Saturday, so **2026-09-07 was the first trading day with v9
live**, and it is the worst Asian day in the series.

**Do not over-read this.** Two trading days and 20 executed trades is not proof
that v9 caused it. What IS established is that the model was rebuilt from
nothing that morning and that the gate's behaviour changed sharply.

### The deeper point about the gate

`re_ml_meta.pkl` records `mean_r` of **-0.083** at every retrain. The model is
regressing R-multiple on a population whose average R is negative — so as it
gets *better* at its job, it predicts "below zero" more often and blocks more.
**The engine is correctly learning that its own signals lose money.** Blocking
more is the model working, not failing.

There is one encouraging sign. Pre-v9 the score was **anti-predictive** —
losers averaged `ml_prob` 0.1485 and winners 0.1079, i.e. it scored losing
trades higher. Under v9 the sign has flipped: losers 0.0409, winners 0.1101.
That is the right direction, on 23 trades, which is far too few to trust.

## 4. Separately: the account balance is corrupt, and it feeds the engine

`vantage_simulation_account.balance` is **-$4,194.40**.

**Thirty trades are recorded closed at a price of $0.00**, the `bugs/025`
signature, totalling **-$1,374.65** of fabricated losses. Three of them landed
on 2026-09-04 and account for **-$1,508.90** between them:

```
1935433548  entry 4478.35  exit 0.00  -$635.80
1935600259  entry 4474.65  exit 0.00  -$609.10
1935267139  entry 4482.10  exit 0.00  -$264.00
```

All-time realised is -$5,028.35, so **roughly 30% of the recorded loss never
happened.** `bugs/025` names only ticket 1935433548; there are thirty.

This matters beyond the ledger, because a negative balance is an input:

- **`equity_drawdown_pct` is an ML feature** (added at v3). It is being computed
  from a corrupt balance, so that feature is garbage for every recent row.
- **Position sizing is a percentage of balance** (`suggest_lot_size(...,
  balance, risk_pct)`), and nothing seen so far guards against balance <= 0.
- **The daily-loss guard is a percentage of balance.** `live_exec_status`
  carries 152 signals blocked by `Trading paused until 22:00 — MT5 order
  blocked`, and the recorded reasons include
  `Daily loss limit hit: $-134322.64 today vs -$54032.46 (40.0% of $135,081.16)`
  and `$-178.45 today vs -$176.59 (20.0% of $882.95)` — a balance that has
  swung between $135,081 and $882.

## What to do, in order

1. **Repair the balance first.** Nothing measured above can be trusted while an
   ML feature, the position sizer and the halt guard all read a number that is
   30% fiction. This is the `bugs/025` repair, widened from one ticket to
   thirty. It needs the owner's sign-off — it is his ledger.
2. **Decide whether v9 stays.** It is two trading days old, it rebuilt the model
   from scratch, and 96% of its training rows carry constants for the five new
   inputs. Reverting to v8 is cheap; the honest alternative is to leave it and
   judge it on a fortnight rather than on a Monday.
3. **Then, and only then, look at payoff.** The engine wins 60% of the time and
   loses money. Until losses stop averaging -1.22R against +0.39R wins, no
   amount of model work makes it profitable. That is a stop-placement and
   exit-management question, not an ML one.

**Nothing in this file has been changed or repaired.** It is a read-only
investigation.

---

# Part 2 — How to fix it (2026-09-08)

The owner's stated purpose: *enter at the right time; re-evaluate resting
orders before they fill; win more than we lose; let the EA template take the
profit.* Each is tested against his data below. **One of the four is already
true, one is the opposite of what the data says, and the two that matter are
not on the list.**

## First, a correction: the ML was not lost with the account change

It was lost on **Saturday 2026-09-05**, by the `re_ml_v9` version bump, which
discards the fitted models by design. `re_ml_meta.pkl`'s history begins
2026-09-07 09:27. The demo account had nothing to do with it: the engine's data
lives in `reversal_engine.db`, which is not split per account, and the new
account's database holds zero trades.

**And the owner is right that this should not happen.** `ml_engine.py` discards
on every bump v3->v9 because a changed feature width or label makes old fitted
models invalid. That reasoning is sound and the consequence is not: it means
every improvement to the model costs the fleet its entire learned state on a
Saturday, with the first live trading day run by a model trained that morning.

**Fix — model handover instead of model deletion.** On a version bump, keep
serving the OLD model while the new one trains in shadow on the back-filled
history, and cut over only when the new model has (a) at least as many labelled
rows as the old had, and (b) a rolling out-of-sample score no worse. Version
bumps stop being a cliff. This is the single most valuable engineering change
on the list and it touches no trading logic.

## "Win more trades than we lose" — already true, and the trap

| | n | share | avg $ | avg pts | avg R |
|---|---|---|---|---|---|
| wins | 442 | **59.4%** | +$35.46 | +3.50 | **+0.642** |
| losses | 302 | 40.6% | -$61.18 | -6.28 | **-1.161** |

He already wins three trades in five. Expectancy is still **-$3.78 a trade**,
because a win returns 0.64R and a loss costs 1.16R.

**At this payoff the break-even win rate is 64.4%.** Chasing win rate is the
trap: the usual way to raise it is a nearer take-profit, which lowers the
payoff and moves break-even further away. **Do not optimise for win rate.**

Two numbers say where the money actually goes:

- **Losses average -1.161R when the stop is 1.0R by definition.** Mean loss is
  6.28 pts against a mean `sl_dist` of 5.75. That extra 0.53 pts per loss, over
  302 losses, is ~160 points of pure leakage — stops slipping or gapping.
  `ml_engine.py` already recorded a worst case of -5.75R.
- **Wins average +0.642R.** They are being closed at two-thirds of the risk
  taken.

**Hold losses to exactly 1.0R and nothing else changes: break-even win rate
falls to 60.9%, against 59.4% actual — nearly there. Take wins to 1.0R as well
and the same 59.4% returns +0.12R per trade, which is a profitable system.**
This is the whole game, and neither half is an ML problem.

## "Let the EA template take the profit" — it is not getting the chance

| max TP hit | n | share | avg net |
|---|---|---|---|
| none | 618 | **83%** | -$7.54 |
| TP1 | 72 | 10% | +$9.73 |
| TP4 | 54 | 7% | +$31.34 |

**83% of executed trades never reach TP1 at all**, yet 59% of them close
positive — so most wins are being taken by something other than the ladder
(trail, breakeven, or a close) at 0.64R. The template's profit-taking is being
pre-empted. Worth establishing WHICH mechanism closes those 442 wins before
changing anything: if it is a breakeven-or-trail rule firing too early, that is
one setting, and it is the highest-value single number in the system.

## "Enter at the right time" — the data names the culprit, and it is the opposite of the guess

Time from signal creation to fill, executed and closed:

| wait to fill | n | win % | total |
|---|---|---|---|
| **under 5 min** | **432** | 58.1 | **-$2,023** |
| 5-15 min | 114 | **71.1** | **+$988** |
| 15-30 min | 75 | 57.3 | -$1,009 |
| 30-60 min | 59 | 62.7 | +$64 |
| over 60 min | 54 | 55.6 | -$214 |

**The trades that fill fastest lose the most.** A fill inside five minutes
means price was already at or through the zone when the signal was made — the
level never held, and the engine is buying into a level that is already
failing. The 5-15 minute bucket, where price left and came back, wins 71% and
is the only sizeable profitable group.

**Counterfactual on his own rows: excluding only the sub-5-minute fills takes
744 executed trades to 302, and the total from -$2,193 to -$170** — from a
clear loss to roughly flat, before any other change.

This is also the strongest evidence that the concern about stale resting orders
is aimed the wrong way: the long waits are not the problem, the instant ones
are.

## "Re-evaluate resting orders before they fill" — worth doing, second in line

The data does not show staleness costing much (>60 min is -$214 over 54
trades), so this is a smaller prize than the entry-timing filter. It is still
correct in principle and it is what `docs/simon-handover/009` already settled
in spirit. Build it AFTER the two above, and make the re-check the same test
the entry filter uses, so there is one definition of "is this level still
valid" rather than two that can disagree.

## One more thing the data says: level_score is not informative

| level_score | n | win % | total |
|---|---|---|---|
| 0.6 | 232 | 56.9 | -$581 |
| 0.7 | 42 | 66.7 | -$7 |
| 0.9 | 400 | 60.5 | **-$1,378** |

The highest-scored band is the biggest loser. Together with `ml_prob` having
been anti-predictive pre-v9, **two of the engine's own confidence measures do
not rank outcomes.** Any ranking work should be validated against realised R
before it is trusted, not assumed from the score's name.

## The order of work

1. **Repair the corrupt balance** (Part 1, section 4). Thirty $0.00 closes,
   -$1,374.65 fabricated, feeding an ML feature, the position sizer and the
   halt guard. Nothing below can be measured honestly until this is done.
2. **Stop losses exceeding 1.0R.** Find why mean loss is 6.28 pts against a
   5.75 pt stop — slippage, gapping, or a stop not where it is believed to be.
   Biggest single arithmetic gain available.
3. **Find what closes the 442 wins at 0.64R** and let the template's ladder
   have them. Combined with (2), this alone turns the current 59.4% win rate
   profitable.
4. **Filter the sub-5-minute fills** — require the level to be left and
   re-approached rather than already breached. Worth ~$1,850 on the measured
   sample.
5. **Model handover instead of deletion** on version bumps, so this never again
   costs the learned state.
6. **Re-validate resting orders** using the same rule as (4).
7. **Then** revisit the ML. It is currently the most honest component in the
   system: it is blocking trades because it correctly learned they lose money.
   Steps 2-4 change what it is learning from, and it should be re-judged after
   them, not before.

**None of steps 2, 3, 4 or 6 is an ML change.** Three are trade management and
one is an entry filter. The ML is not what is broken.

---

# Part 3 — Execution log (2026-09-08)

Owner: *"fix it all"*. Steps 2, 3, 4 and 6 change order placement or exits, so
each is built test-first and none is live until demoed. This section records
what is done, what is blocked and why, in the order the work actually has to
happen.

## Step 0 (unplanned, and it gates 2 and 3) — the measurement was never taken

**DONE 2026-09-08.**

Before writing any exit change it was worth checking what evidence existed for
it. There is almost none. `mfe_pts`/`mae_pts` — how far a signal ran each way —
are recorded by `record_excursion`, which is called from exactly one place:
`_manage_triggered_signal`. That function's own docstring says live-executed
signals "are routed to `_reconcile_live_signal` instead, **never here**".

Measured on the owner's rows:

| | |
|---|---|
| executed signals | 745 |
| carrying an MFE | **52** |
| carrying an MFE, September | **0** |
| usable for a breakeven decision | **35** |

So the live path has never measured itself. `_manage_ref_ladder_signal`'s own
comment states the consequence: *"without it, any change to stop width or
target distance is a guess"*.

**Changing an exit rule on 35 samples would have been that guess.** Fixed
first: `_record_live_excursion` now widens both watermarks on every cycle a
live signal is still open, measured from `trigger_price` (the realistic fill)
exactly as the virtual path does. Seven tests, five mutants killed. It records
only — no stop moves, nothing closes, and it is wrapped so a measurement can
never cost a live trade its management.

**Consequence for the plan: steps 2 and 3 need roughly two weeks of live
running to gather the evidence they should be decided on.** That is not a
delay that can be engineered away; it is the cost of the instrument having been
absent.

## What the existing evidence does and does not support

The strongest signal available today is the breakeven split, on 441 wins:

| | n | avg R | avg $ |
|---|---|---|---|
| won, stop never moved to BE | 315 | **+0.767** | +$42.15 |
| won, stop moved to BE | 126 | **+0.333** | +$18.99 |

Suggestive, and **not sufficient**. Trades that reach breakeven are a selected
population — they went far enough into profit to trigger it — so some of that
126 would have been losses without it. The naive reading ("BE costs $23 a
trade, therefore $2,918") is wrong for exactly that reason, and the honest
number needs the MFE data step 0 has only just started collecting.

The 35 samples that do have MFE hint the same way (MFE 1.039R, realised
0.464R, 0.575R left on the table) and 35 is not enough to move a live stop
rule.

## Status of each step

| # | step | state |
|---|---|---|
| 0 | live excursion recording | **DONE**, tests + mutants |
| 1 | repair the corrupt balance | **BLOCKED on the owner** — it is his ledger, 30 rows |
| 2 | stop losses exceeding 1.0R | **BLOCKED on step 0's data** (~2 weeks) |
| 3 | stop cutting wins at 0.64R | **BLOCKED on step 0's data** (~2 weeks) |
| 4 | filter sub-5-minute fills | ready to build — the evidence is already sufficient (432 trades, -$2,023) |
| 5 | model handover, not deletion | ready to build — no trading logic |
| 6 | re-validate resting orders | after 4, sharing its rule |
| 7 | revisit the ML | after 2-4 change what it learns from |

**Steps 4 and 5 are the next two, and 5 touches nothing that trades.**


---

**Tracked from here:** the open items moved to
[docs/todo/reversal-engine/](../reversal-engine/README.md) on 2026-09-08 so
they live somewhere a person would look for work rather than at the end of an
investigation. This file stays as the evidence they rest on.
