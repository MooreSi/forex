# 010 — Thirty trades are recorded closed at $0.00

**Status:** open. **Needs the owner** — it rewrites his trading history, and it
asks a question only he can answer.
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
