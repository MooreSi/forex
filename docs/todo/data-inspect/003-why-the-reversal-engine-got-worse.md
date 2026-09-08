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
