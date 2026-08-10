# Q001 — The six trading / ops defaults

**Decision:** PROVISIONAL — recommendations adopted 2026-08-10 (Darren, on the
brother's behalf, so work could proceed). Awaiting the brother's confirmation.
**Who decides:** the brother (trading/business calls).
**Consumed by:** review-august-08 phase 1 (010/030/060) and phase 2 (050/070).
**Full detail & the option write-ups:** the review pack's
[QUESTIONS.md](../todo/review-august-08/QUESTIONS.md) — this file is the
single-page summary for the answer pass; that file has the reasoning.

## The six, and what we're proceeding with

| # | Question | Provisional answer | If the brother says otherwise |
|---|---|---|---|
| 1 | How does an order carry its id at the broker? | Both order comment **and** magic number | Change the stamping in phase1/010 before it ships |
| 2 | Reconciliation: report-only first, how often? | Report-only for the first week, then repair; every 60s | Flip repair on sooner / change interval (a tunable) |
| 3 | Protective-halt default limits | 3% daily loss / 10% drawdown / 3 consecutive losses; pause opens only | Re-set the three numbers (tunables) before phase1/060 ships |
| 4 | Backups: where and how often? | Daily snapshot to a second local folder, keep 30 | Change destination/cadence in phase2/050 |
| 5 | Auto-update channel: kill or harden? | Disable now, decide hardening later | Harden or remove instead in phase2/070 |
| 6 | Broker position with no id (manual trade) | Watch only (`recovered-manual`), never auto-manage | Adopt-fully / ask-per-position in phase1/030 |

## Why these are safe to proceed on

Every one is either report-only, off-by-widening (bind/update disabled), or a
tunable that keeps trading strictly *more* conservative than today. None of them
can make the system trade more aggressively than it does now on their own —
which is what makes them safe provisional defaults while the brother is away.

The money-path tasks that consume these (order dedup, reconciliation, halts)
**still** need the brother's sign-off + a demo session before they ship,
independent of confirming the numbers here.
