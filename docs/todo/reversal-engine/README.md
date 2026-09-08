# Reversal Engine — making it profitable

Raised 2026-09-08 from [data-inspect/003](../data-inspect/003-why-the-reversal-engine-got-worse.md),
which measured the engine against the owner's own rows rather than against the
code's intentions. Read that first; these are its open items.

**The one number that frames all of it:** the engine already wins **59.4%** of
executed trades and still loses **$3.78 a trade**, because a win returns
**0.642R** and a loss costs **1.161R**. Break-even at that payoff needs 64.4%.

**So do not optimise for win rate.** The usual way to raise it is a nearer
take-profit, which lowers the payoff and moves break-even further away. Hold
losses to 1.0R and break-even falls to 60.9%; take wins to 1.0R as well and the
current win rate returns +0.12R a trade.

| # | item | state |
|---|---|---|
| — | live excursion recording | **DONE** 2026-09-08 (`9b5fbd5`) |
| — | model handover on a version bump | **DONE** 2026-09-08 (`95e2639`) |
| [010](010-repair-the-fabricated-losses.md) | repair 30 fabricated $0.00 closes | **needs the owner** |
| [020](020-losses-exceed-the-stop.md) | losses average -1.161R against a 1.0R stop | blocked ~2 weeks on data |
| [030](030-wins-are-cut-at-two-thirds-of-a-r.md) | wins closed at 0.642R | blocked ~2 weeks on data |
| [040](040-filter-the-instant-fills.md) | sub-5-minute fills lose $2,023 | **ready to build** |
| [050](050-revalidate-resting-orders.md) | re-check a resting order before it fills | after 040 |
| [060](060-revisit-the-ml.md) | revisit the ML gate | after 020-040 |
| [070](070-share-training-data-with-the-fleet.md) | ship the fleet's learning to every client | **designed, needs one decision** |

**040 is the next one to build.** 020 and 030 cannot honestly be decided until
the excursion recording landed on 2026-09-08 has run for a fortnight.
