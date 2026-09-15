# 036 — How few trades is too few to report a number?

**Status:** **OPEN.** Proceeding on a provisional default of **20 trades per
side**. Change it by saying a number; nothing else has to change with it.
**Money:** not directly — the backtest places nothing. It is about when a
backtest figure is allowed to influence which template trades real money.
**Raised:** 2026-09-15, writing `docs/todo/003-in-sample-out-of-sample-split.md`.

## The question

Spec 003 splits a backtest into an in-sample half and an out-of-sample half and
reports both. Splitting halves the trade count on each side. A template that
filled 40 trades over the window becomes two sides of about 20.

At some count, a win rate and a profit factor stop being information. Four
trades at 75% is not a 75% win rate; it is three wins. The question is where
that line sits **for you** — below what count should the report refuse to print
a figure and say why instead?

## Why it is yours and not mine

It is not a computation, it is a risk appetite. Set it high and the split will
frequently refuse to report anything, which is safe but useless on a
thin window. Set it low and you will be shown percentages built on a handful of
trades, which is worse than being shown nothing, because a number on screen
beside another number invites a comparison the data cannot support. That is the
same failure already recorded in the analytics domain file: a row of zeros
beside a row showing 62.8% drawdown read as an argument for the template that
was never simulated at all.

## What the rest of the system does

Nothing that transfers directly, but for calibration:

- `reversal_engine/meta_label.py` sets `DEFAULT_MIN_SAMPLES = 200` before it
  will arm a model. That is a machine-learning gate on a 33-feature vector, not
  a win rate, so 200 is far stricter than this needs.
- `database.py` carries `_CHANNEL_MIN_SAMPLE` and `_CHANNEL_TRUST_MIN_SAMPLES`
  for channel trust scoring — the closest existing analogue, and worth reading
  the values of before you pick.

## The provisional default and what it does

**20 trades.** A side with fewer than 20 filled trades reports no win rate, no
profit factor and no P&L; it reports the count and the sentence "too few trades
to measure". The other side is still reported if it clears the bar.

20 is chosen to be visibly arbitrary rather than falsely precise. It is roughly
where a 60% win rate and a 50% win rate stop being distinguishable by eye, and
it keeps a typical 40-trade window reportable on both sides.

## What I need from you

One of:

- a number, or
- "report it anyway, with the count shown" — in which case the refusal is
  dropped and every figure is printed with its trade count beside it, or
- "refuse below N on the out-of-sample side only" — the in-sample side is
  already contaminated by the tuning, so a thin in-sample figure misleads less
  than a thin out-of-sample one.

Until then the report will say `min 20 (provisional — see handover 036)` next
to any side it refuses, so the default is visible on screen rather than buried
in a constant.
