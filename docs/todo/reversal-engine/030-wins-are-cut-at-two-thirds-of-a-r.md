# 030 — Wins are closed at 0.642R, and 83% never reach TP1

**Status:** open, **blocked on data until roughly 2026-09-22.**
**Money:** yes — it is where profit is taken.

## The measurement

442 executed wins average **+0.642R**. And the ladder is barely used:

| max TP hit | n | share | avg net |
|---|---|---|---|
| none | 618 | **83%** | -$7.54 |
| TP1 | 72 | 10% | +$9.73 |
| TP4 | 54 | 7% | +$31.34 |

**83% never reach TP1, yet 59% close positive** — so something other than the
EA template's ladder is taking the profit.

## The suspect, and why it is not yet proven

Splitting the 441 wins by whether the stop was moved to breakeven:

| | n | avg R | avg $ |
|---|---|---|---|
| BE never moved | 315 | **+0.767** | +$42.15 |
| BE moved | 126 | **+0.333** | +$18.99 |

Suggestive and **not sufficient**. Trades reaching breakeven are a SELECTED
population — they went far enough into profit to trigger it — so some of that
126 would have been losses without it. The naive reading ("BE costs $23 a trade,
so $2,918") is wrong for exactly that reason.

The 35 trades that do carry MFE hint the same way (MFE 1.039R, realised 0.464R,
0.575R left on the table). **35 is not enough to move a live stop rule.**

## What settles it

The excursion data from 2026-09-08 onward. For each win, compare `mfe_pts` to
what was realised: if BE-moved trades show a large gap and non-BE trades do
not, the breakeven trigger is the cause and its distance is the one number to
change.
