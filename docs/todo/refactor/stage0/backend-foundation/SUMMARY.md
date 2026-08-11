# Backend Foundation — the changes, in plain English

A per-mechanism breakdown of what's changing and why — no jargon, no code. Full detail lives in
the task files; this is the digest.

---

## 1. How the database is accessed

**Problem:** Every part of the app opens raw database connections by hand, with no shared
safety net. One known consequence: closing a signal updates its status and updates the
account balance as two separate, unconnected database writes — if the app crashed between
them, the two would disagree with each other.

| Change | Before | After |
|---|---|---|
| Database access | Each engine writes its own raw SQL calls directly | A single shared layer owns all the database calls, with a consistent way to group related writes together |
| Multi-step updates (e.g. closing a trade) | Two separate, unconnected writes | One grouped write that either fully succeeds or fully fails together |

## 2. Test safety net before anything changes

**Problem:** The GD Copy signal engine has zero automated tests today. Restructuring it
without first writing down what it currently does is how a working feature quietly breaks.

| Change | Before | After |
|---|---|---|
| Test coverage for GD Copy | None | A full suite that pins down exactly how it behaves today, including the money math (partial closes, balance updates) |

## 3. Breaking up the GD Copy engine's code

**Problem:** GD Copy's main file is 1,295 lines doing three different jobs at once (deciding
when to fire signals, managing stop-loss/take-profit levels, and tracking correlation against
the real trading channel it's modeled on).

| Change | Before | After |
|---|---|---|
| File structure | One 1,295-line file | Several smaller files, each doing one job, none over 800 lines |
| Behavior | (baseline) | Identical — proven by re-running the same test suite from step 2 against the new structure |

## 4. Proving it works for real (gated — needs your go-ahead)

**Problem:** Tests can prove the new code behaves like the old code, but only a real run
against MetaTrader proves it actually works end-to-end.

| Change | Before | After |
|---|---|---|
| Real-world validation | Not yet done | One test run against a demo account (not the live one), only after you've reviewed and approved this specific step |

---

*Scope:* GD Copy signal engine only — its database access and its internal code
structure. **Not doing:** any change to the other three engines, the trading UI, the
MetaTrader companion program, or anything on the live app you're trading with tonight.
