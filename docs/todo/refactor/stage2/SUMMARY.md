# Road to handoff — plain-English summary

**For:** Darren (and Simon) · **Updated:** 2026-08-11 (scaffold — nothing built yet)

## What this is

A single clear plan for everything that needs to happen to turn this refactored app into something
you can hand to Simon. You can now run it, but you said you can't tell what you're meant to do — so
that's the first thing this fixes, followed by the foundations, the cleanup, and the safety.

## The seven pieces, one line each

1. **Make it understandable** — a first-run "Start Here" checklist, a Help button, plain-language
   tab names, and screens that tell you what to do next instead of just saying "nothing here yet".
2. **Proper database upgrades** — move the ~90 ad-hoc table changes out of one giant file into
   proper numbered migrations that can't silently half-apply.
3. **Trustworthy tests** — delete 13 test files that look like tests but check nothing, cover the
   money code properly, and tidy the test folders.
4. **Split the big files** — the settings screen alone is 3,000+ lines; break the giant frontend
   files apart and finish the reorganisation that stalled.
5. **Make the offline mode actually work** — wire a fake market so debug mode shows live-looking
   prices and can run a full trade start-to-finish with no real broker.
6. **Make it safe with real money** — the order-safety fixes (never place a trade twice, never lose
   track of a position, brakes on by default). These need Simon at a demo terminal to sign off.
7. **A clean handoff** — the HANDOFF file (done), a "ready to give to Simon" checklist, and up-to-date
   docs.

## What it will NOT do

- No new trading strategies or changes to how it decides trades.
- Nothing places, closes or sizes a real or demo order except the piece Simon signs off in step 6.

## What we need from you

- Answer the short [QUESTIONS.md](QUESTIONS.md) (each has a recommendation).
- The frontend split (step 4) is waiting on 4 small naming/structure answers.
- Simon confirms the money-path settings and joins a demo session for step 6.

## Where to start

Step 1 (usability) — it's your top pain, it's pure display code, and it touches no money.
