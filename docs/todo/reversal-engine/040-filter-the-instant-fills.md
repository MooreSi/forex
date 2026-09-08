# 040 — Trades that fill in under five minutes lose $2,023

**Status:** **READY TO BUILD.** The evidence is already sufficient; this one is
not waiting on anything.
**Money:** yes — it stops orders being placed. It makes the app trade LESS,
never more, which is the safe direction, but it still wants a demo.

## The measurement

Time from signal creation to fill, executed and closed:

| wait to fill | n | win % | total |
|---|---|---|---|
| **under 5 min** | **432** | 58.1 | **-$2,023** |
| 5-15 min | 114 | **71.1** | **+$988** |
| 15-30 min | 75 | 57.3 | -$1,009 |
| 30-60 min | 59 | 62.7 | +$64 |
| over 60 min | 54 | 55.6 | -$214 |

**The fastest fills lose the most.** A fill inside five minutes means price was
already at or through the zone when the signal was made — the level never held,
and the engine is buying into a level that is already failing. The 5-15 minute
bucket, where price left and came back, is the only sizeable profitable group.

**Counterfactual on the owner's rows: excluding only the sub-5-minute fills
takes 744 executed trades to 302 and the total from -$2,193 to -$170** — from a
clear loss to roughly flat, before any other change.

## What to build

Require the level to have been LEFT and re-approached rather than already
breached. The rule wants to be one function, because
[050](050-revalidate-resting-orders.md) has to use the same one — two
definitions of "is this level still valid" that can disagree is how this class
of bug starts.

Do not implement it as a fixed five-minute timer if a cleaner condition
expresses it (price having traded away from the zone by some distance before
returning). The five-minute figure is the symptom that located it, not
necessarily the right rule.

## Test first, then demo

It gates order placement. Tests before code, and it does not go live without
the owner watching.
