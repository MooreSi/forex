# 049 — `gross_pnl` and `realised_pnl` are never corrected, and nothing reads them

**Status:** found 2026-09-12 sweeping the live trade ledger for the bug classes
that have recurred (016 phantom open rows, 025 zero-price closes, 028 double
bookings). **Not fixed** — the fixes are a write to his money records or a
change on the close path.
**Touches money:** **no, and that was checked rather than assumed.** Every
money-path reader — the daily-loss halt, the give-back guard, the History
figures, the per-engine P&L — reads `net_pnl` or `mt5_profit`, which
`profit_sync` does correct.
**Severity:** low today, and a landmine for the first report that reads the
wrong column.

## What the sweep found

295 closed trades, 2026-09-03 to 2026-09-11. Clean on the recurring classes:

| checked | result |
|---|---|
| open rows with no live position (bugs/016) | 0 — every row is closed |
| duplicate `mt5_ticket` (bugs/028) | 0 |
| rows with no ticket at all | 0 |
| `mt5_profit` disagreeing with `net_pnl` by >$1 | 0 |

Two columns are not clean.

## 1. `gross_pnl` still holds the 2026-09-04 fiction

Three rows carry a `gross_pnl` of **-$44,821.00, -$44,783.50 and -$44,746.50**.
They are the bugs/025 trades: closed as `closed_while_disconnected` with
`close_price = 0.0`, so the entry-versus-exit arithmetic was done against zero
and produced contract-value-sized losses.

`profit_sync` later corrected them. It corrects `net_pnl` and `mt5_profit`, and
those rows now read -$264.00, -$635.80 and -$609.10, which are the real losses.
**`gross_pnl` was not part of that correction and still is not.**

Across the whole ledger: `SUM(net_pnl)` is **-$3,902.32** and `SUM(gross_pnl)`
is **-$140,242.20**. The $136,340 difference is almost entirely those three
rows.

## 2. `realised_pnl` is the pre-correction estimate on 114 of 295 rows

Same cause, smaller numbers: `profit_sync` replaces `net_pnl` with the broker's
figure and leaves `realised_pnl` holding whatever the app computed at close
time. Usually a few cents. Once it is $54 **and the opposite sign** — trade
`058ee59e`, `realised_pnl` +3.11 against `net_pnl` -50.90. The estimate says
that trade won; the broker says it lost.

## Why it is harmless today, and what makes it a landmine

`gross_pnl` is written in four places and **read in none** — not by a service,
not by a controller, not by a panel, not by the consolidated ledger. It is a
write-only column.

`realised_pnl` has exactly one live reader, `monitor_loop`'s profit-close
check, and that reads it on an **open** trade, where it holds partial-close
proceeds and `profit_sync` has not run. Correct use.

So nothing is wrong on any screen. The trap is that both columns look
authoritative to anyone who opens the database or writes the next report, and
one of them is wrong by $136,340.

**The near miss worth recording:** `risk/repo.sum_realised_pnl_since` is what
the daily-loss halt sums. Its name says `realised_pnl`; its SQL says `net_pnl`.
A tidy-up that made the name and the column agree would have switched a
protective limit onto the stale estimate, and nothing would have caught it —
every existing test of the halt monkeypatches that function away. It is now
pinned behaviourally, with the sign-flip row above as one of the cases, and
the function says in its own docstring why it reads the column it does.

## The three options

1. **Correct both columns in `profit_sync`**, alongside `net_pnl`. Honest, and
   it is an edit to the close-path's correction step.
2. **Stop writing `gross_pnl`.** Nothing reads it; a column that is written,
   never read and sometimes wrong is worse than no column. This is a schema
   change and a migration.
3. **Leave them and write down that they are estimates**, which is the cheapest
   and is what this file is until a decision lands.

Whichever: the three 2026-09-04 rows are historical, and correcting them means
writing to his money records. That is not something to do unattended.
