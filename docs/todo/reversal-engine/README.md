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
| [040](040-filter-the-instant-fills.md) | sub-5-minute fills lose $2,142 | **BUILT**, off by default, not demoed |
| [050](050-revalidate-resting-orders.md) | re-check a resting order before it fills | **BUILT**, shares the bias-gate toggle, not demoed |
| [060](060-revisit-the-ml.md) | revisit the ML gate | after 020-040 |
| [070](070-share-training-data-with-the-fleet.md) | ship the fleet's learning to every client | **designed, needs one decision** |
| [080](080-no-trend-gate-on-the-telegram-path.md) | no trend filter on the Telegram path | **BUILT + all four order routes covered**, off by default, not demoed |
| [090](090-level-score-bypasses-the-bias-filter.md) | `level_score` switches off the bias filter | **BUILT**, off by default, not demoed |
| [100](100-revalidating-every-waiting-order.md) | re-evaluate a waiting order before it becomes a trade | **BUILT** — the Telegram path re-checks schedule, news and fill delay |
| [200](200-what-a-professional-desk-would-add.md) | design note: what a professional desk would add, and in what order | design |
| [210](210-what-was-built.md) | what shipped 2026-09-11, and the switches still waiting on a demo session | **BUILT, all off by default** |

## Picking this up again

**080 and 090 are built and live** (owner turned the gate on 2026-09-09), and
all four order routes now consult one rule. Neither has been demoed.

**Next: [060](060-revisit-the-ml.md)** — but only after 020 and 030, which
unblock around 2026-09-22 when the excursion data has accumulated. It is the only item
whose evidence is already sufficient, it is worth about $1,850 on the measured
sample, and it makes the app trade less rather than more.

**020 and 030 unblock around 2026-09-22.** They need the excursion data, which
started being collected when the app was restarted at **09:05 on 2026-09-08**
— before that restart the live path had never recorded how far a trade
travelled. Check the coverage before relying on it:

```sql
SELECT COUNT(*), SUM(mfe_pts IS NOT NULL)
FROM re_signals WHERE close_time > strftime('%s','2026-09-08') AND live_exec_status='executed';
```

**[010](010-repair-the-fabricated-losses.md) and [070](070-share-training-data-with-the-fleet.md)
are waiting on the owner**, not on work. 010 asks how to repair thirty trades
the broker has no closing deal for; 070 asks how much a client should trust
other clients' data, and both are in `docs/simon-handover/` too
([028](../../simon-handover/028-sharing-the-engines-learning-with-every-client.md)).

## What was done on 2026-09-08

| commit | |
|---|---|
| `9b5fbd5` | live excursion recording — the live path had never measured itself |
| `95e2639` | model handover on a version bump, and the ML gate no longer fails open |
| `041c6a7` | these items |
| `4e10467` | the fleet-sharing design |

The app was restarted at 09:05 to pick up the first two. Nothing else about
its trading behaviour changed.
