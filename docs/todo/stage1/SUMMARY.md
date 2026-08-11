# Review remediation — plain-English summary

**For:** Darren · **Updated:** 2026-08-08 (scaffold — nothing built yet)

## What this pack does

The August review found the app's structure is good, but four things make it unsafe to keep
building on: it can accidentally place the same trade twice; its records can disagree with the
broker's records with nothing to catch it; its safety brakes are switched off by default; and two of
the scripts that are supposed to catch mistakes have been silently broken (they always say "all
good"). This pack fixes those in strict order, before any new features.

## The phases, in one line each

1. **Stop the bleeding** — make double-orders impossible, make the app's books always match the
   broker's, turn the safety brakes on, and make the dashboard reachable only from this machine.
2. **Safety net** — fix the broken checker scripts so green means green, give the database a proper
   upgrade path and a daily backup, and switch off the unsecured auto-update channel.
3. **Expansion tax** — delete ~2,800 lines of dead code, de-duplicate the signal engines' shared
   maths, and restart the frontend restructure that was planned but never begun.
4. **Hygiene** — automatic checks on every commit, tidy the test layout, real licence signing.

## What it will NOT do

- It never changes trading strategy, signal quality, or position sizing maths.
- The frozen close path stays untouched.
- Nothing in this pack places, closes, or modifies any real or demo order; the trade-path changes
  each end with a supervised demo session before they count as done.

## What I need from you

- Answer the six questions in [QUESTIONS.md](QUESTIONS.md) (each has a recommendation — "go with
  the recommendations" is a complete answer).
- A demo session + your sign-off for each money-touching task before it's called done.
