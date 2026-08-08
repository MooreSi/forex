# System Review — Questions & Best-Practice Checklist

**Date:** 2026-08-08
**Purpose:** the question list this review was run against. Each area report
(backend, frontend, risk, data, testing, security-ops) answers its slice of
these. Anything unanswered is listed in that report's "Open questions".

The bar being applied: this is a system that places real orders with real
money, that the owner intends to expand significantly. So the review optimizes
for two things: **(1) nothing in the current system can silently lose money**,
and **(2) the structure can absorb growth without each new feature getting
more expensive to add.**

---

## 1. Money safety (risk-review.md)

- [ ] Where exactly are the only code paths that can send, modify, or close a
      real order? Is that set small, known, and hard to reach by accident?
- [ ] Is the frozen close path (`close_trade`, `record_close`,
      `_make_close_trade_ctx`, `partial_close_trade`) still intact and single-copy?
- [ ] Can a demo/test/backtest signal ever reach the live order path? What flag
      separates them, and is it checked at the *last* step before send?
- [ ] Is order send idempotent? Can a retry, a reconnect, or a duplicate signal
      double-fire an order?
- [ ] What happens on: partial fill, requote, broker reject, disconnect
      mid-order, app crash with open positions, app restart?
- [ ] Is there reconciliation between DB state and broker state on startup?
- [ ] Are there hard limits enforced in code (not just config): max lot, max
      open positions, daily loss cap, kill switch?
- [ ] Are prices/lots handled with correct precision and broker-step rounding?

## 2. Architecture & backend (backend-review.md)

- [ ] Are the stated layer rules (frontend → controllers → services → db,
      never up, four import bans "enforced at zero") actually true today?
- [ ] Which files exceed the project's own 800-line split rule, and what do
      they hide?
- [ ] Is there dead/orphaned code nothing imports? (This bit the project
      before: ~3,000 orphaned lines found in a past audit.)
- [ ] Do the three signal engines (breakout, reversal, signals) duplicate
      logic that should be shared, or share state they shouldn't?
- [ ] Are exceptions swallowed anywhere near broker/order code?
- [ ] Threading/async: what shared mutable state exists, and what guards it?
- [ ] Is configuration one coherent system, or config.yaml + scattered
      constants + per-page tunables?

## 3. Frontend (frontend-review.md)

- [ ] What does spec 001-frontend-restructure call for, and how far along is it?
- [ ] settings.py is 3,112 lines and components/ is empty — how much UI is
      duplicated across pages that should be shared components?
- [ ] Does the frontend only ever talk to controllers?
- [ ] Do UI callbacks block the event loop or swallow exceptions (a silent UI
      is dangerous when it's the window onto live trades)?
- [ ] What fraction of pages have any test at all?

## 4. Data (data-review.md)

- [ ] Is there a schema-migration story for installed instances, or does an
      update risk breaking a live user's DB?
- [ ] Is trade open/close recorded atomically relative to the broker action?
      Can a crash leave DB and broker disagreeing?
- [ ] SQLite under concurrency: WAL, busy timeout, who else holds long
      transactions while the trade path wants to write?
- [ ] Could retention ever purge records needed to audit live trades?
- [ ] Is there any backup of the live DB?
- [ ] Cluster sync: what happens when two nodes diverge?

## 5. Testing & guardrails (testing-review.md)

- [ ] Do the four gates and the coverage ratchet scan paths that still exist?
      (A guardrail here once scanned a deleted directory and said "all good"
      for months — every gate gets re-verified against today's tree.)
- [ ] Which services/pages have zero tests, and is any of that money-path code?
- [ ] Could any test, under any misconfiguration, reach a real MT5 terminal?
- [ ] Is there CI, or does everything depend on the developer remembering
      `python -m tools.checks all`?
- [ ] Are dependencies pinned and reproducible?

## 6. Security & operations (security-ops-review.md)

- [ ] What does :8888 bind to, and is there any authentication in front of a
      UI that can trade real money?
- [ ] What can a remote/cluster peer make this node do, and what authenticates
      the peer? Any unsafe deserialization of remote payloads?
- [ ] Where do real secrets live (broker creds, Telegram token, licence key)?
      Are any committed, or leaked into latest_logs/?
- [ ] Can inbound Telegram messages trigger actions, and who is authorized?
- [ ] Is the update path integrity-checked, or could a hijacked update run
      arbitrary code next to a live account?

---

## Best-practice bar used for severity ratings

| Severity | Meaning here |
|---|---|
| **Critical** | Can lose money, fire an unintended order, or hand control of a live account to someone else. Fix before any new feature work. |
| **High** | Can mis-size, fail to close, corrupt/lose trade records, or will make every future feature more expensive. Fix in the next 1–2 working sessions. |
| **Medium** | Structural debt: oversized files, duplication, missing tests on non-money paths. Schedule; fold into the restructure. |
| **Low** | Hygiene: naming, docs, minor duplication. Fix opportunistically. |
