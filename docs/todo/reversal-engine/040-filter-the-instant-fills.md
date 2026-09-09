# 040 — Trades that fill in under five minutes lose $2,023

**Status:** **BUILT 2026-09-09, off by default, NOT DEMOED.** Turn it on at
Trading > Strategy > Risk Settings, "Ignore signals that fill immediately".
See *Built* at the bottom — **the mechanism proposed in this file was tested
and rejected**, and the filter shipped as an empirical rule instead.
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


---

## Built 2026-09-09 — and the explanation in this file is wrong

### The evidence re-measured, and it held

| time to fill | n | win % | total |
|---|---|---|---|
| **under 5 min** | **443** | 57.8 | **-$2,142.30** |
| 5-15 min | 115 | **71.3** | **+$1,041.07** |
| 15-30 min | 75 | 57.3 | -$1,009.18 |
| over 30 min | 114 | 58.8 | -$198.73 |

**And it is stable**, which this file had not checked:

| | fast (<5m) | 5-15 min |
|---|---|---|
| 2026-07 | -$372.35 | +$14.26 |
| 2026-08 | -$1,376.99 | +$827.87 |
| 2026-09 | -$392.96 | +$198.94 |

Fast loses every month; 5-15 wins every month. The five largest winners in that
bucket are $153/$132/$132/$122/$90 against a $1,041 total, so no outlier is
carrying it.

### The mechanism this file proposed does not survive contact with the data

The claim above was: *"A fill inside five minutes means price was already at or
through the zone when the signal was made -- the level never held."* That is
directly testable, because `re_signals` records `price_at_signal` alongside the
entry zone. Splitting the same population on exactly it:

| | n | win % | per trade |
|---|---|---|---|
| price already in/through the zone | 208 | 57.7 | -$3.55 |
| price still away from the zone | 549 | 59.7 | -$2.91 |

**It separates almost nothing**, both sides lose, and it accounts for only 208
of the 443 fast fills. So the proposed cause is not the cause, and this file's
suggestion to express the rule as "left the zone and came back" would have
built on it.

### What shipped instead

`governor.fill_too_soon(created_at, now, rs)` — a plain minimum delay between a
signal being created and its entry being reached, **stated as empirical**: a
consistent effect with no established mechanism. Two settings, migration 36:
`min_fill_delay_enabled` (off) and `min_fill_delay_s` (300).

**The window is configurable precisely because the cause is unknown.** A rule
that cannot be explained should be easy to turn off and easy to retune, rather
than a constant buried in the code.

Fails open on anything it cannot judge — no creation time, a zero window, a
clock that ran backwards — the same rule the bias gate follows: a risk filter
that refuses on missing DATA stops all trading the moment a field is absent.

20 tests, red first. Five mutants killed, **one after strengthening a test that
passed for the wrong reason**: the missing-creation-time case used a large
`now`, so the elapsed time cleared any window on its own and the guard could be
deleted unnoticed. The added case uses a small clock, where an absent field
would otherwise read as "created at the epoch".

### Still to do

Wired into the Reversal Engine's live-execution path only. **[050](050-revalidate-resting-orders.md)
should share this same function** rather than growing its own copy — that is
the whole point of it.
