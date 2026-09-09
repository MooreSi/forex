# 010 — Thirty trades are recorded closed at $0.00

**Status:** FIXED 2026-09-09 on the owner's instruction (*"fix it but don't
lose valid trade data"*). **The question below turned out not to need
answering** — see "What it actually was".
**Money:** yes. The fabricated total is **-$1,374.65**, about 30% of the
account's all-time recorded loss of -$5,028.35.
**Found:** 2026-09-08, data-inspect/003.

## What is wrong

`forex_trader_demo.db` holds **30 closed trades with `close_price <= 0`** — the
`bugs/025` signature. Three landed on 2026-09-04 and account for -$1,508.90:

```
1935433548  entry 4478.35  exit 0.00  -$635.80
1935600259  entry 4474.65  exit 0.00  -$609.10
1935267139  entry 4482.10  exit 0.00  -$264.00
```

`bugs/025` names only the first. There are thirty.

## Why it is not just a wrong number on a screen

`vantage_simulation_account.balance` is **-$4,194.40**, and that balance is:

- an **ML feature** — `equity_drawdown_pct`, added at v3, so every recent
  training row carries a corrupt value;
- the **denominator for position sizing** — `suggest_lot_size(..., balance,
  risk_pct)`, with no guard seen against balance <= 0;
- the **denominator for the daily-loss halt**. 152 signals carry
  `Trading paused until 22:00 — MT5 order blocked`, and the recorded reasons
  include `$-134322.64 today vs -$54032.46 (40.0% of $135,081.16)` and
  `$-178.45 today vs -$176.59 (20.0% of $882.95)`.

## The question only the owner can answer

The broker has **no closing deal** for these tickets. So a repair is one of:

- **A. Reopen them** — they were never closed, so restore `status='open'` and
  remove the fabricated P&L. Truthful, but it resurrects positions that may
  since have really closed.
- **B. Zero the P&L, leave them closed** — keeps the ledger tidy and stops the
  balance being fiction, at the cost of recording a close that has no deal
  behind it.

**Neither has been done. Nothing in his database has been touched.**

## When it is done

Take a copy of the database first, show the exact before/after for all thirty
rows, and check whether `trade_pause_until` or `risk_halt_reason` were set off
the back of them.


---

## What it actually was (2026-09-09)

The diagnosis above was built from `close_price <= 0`, and that was the wrong
detector. Measuring instead by *disagreement between the columns*:

| database | closed rows | `sum(realised_pnl)` | `sum(net_pnl)` = broker | rows wrong |
|---|---|---|---|---|
| `forex_trader_demo.db` (pre-migration) | 1,398 | **-197,948.55** | -2,209.85 | **7** |
| `forex_trader_demo_26004592.db` (active) | 206 | **-136,445.76** | -3,647.37 | **3** |

**`realised_pnl` was the only corrupt column.** `net_pnl` and `mt5_profit`
already carried the broker's real figure on every one of those rows. The
fabricated value is the entry price multiplied by the position size and
negated — the arithmetic of closing at 0.00 — so `4482.10` became
`-44,821.00`.

The three rows in the ACTIVE database are exactly the three tickets named
above, and their true values sum to **-$1,508.90**, matching this file's own
figure. Two more in the old database had `close_price == entry_price` rather
than zero, so `close_price <= 0` would never have found them.

## What was done

`realised_pnl := net_pnl` on the 10 divergent rows, and nothing else.

- **Nothing was deleted and nothing was reopened.** Row counts are unchanged:
  1,398 and 206. The owner's instruction was *don't lose valid trade data*,
  and no trade data was touched — only a derived number that disagreed with
  the broker.
- **Option A vs B never arose.** Both assumed the broker had no P&L for these
  tickets. It has: `mt5_profit` is populated on all ten.
- Both databases were copied first (`*.db.bak-20260909-160157`), and the
  before/after for every row was printed and is in the session record.

Result: `sum(realised_pnl)` -197,948.55 → **-1,841.16** (old) and
-136,445.76 → **-3,603.66** (active). The small residual gap against
`net_pnl` is ordinary gross-vs-net variation on rows that were never corrupt.

## Still open

The **balance** question. `vantage_simulation_account.balance` in the old
database is -$4,904.89, which is fiction inherited from the same arithmetic.
The active database's balance is $852.19 and **matches the broker exactly**,
so the live path is correct and nothing was changed there. The old database is
no longer traded from; its balance is only history.
