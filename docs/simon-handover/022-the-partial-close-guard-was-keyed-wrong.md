# 022 — the guard I built this morning would have cost you money

**Status:** found and fixed 2026-09-01, overnight. **Nothing was damaged.**
**Money:** yes. Read this one.
**Needs a decision from you:** no, but you should know it happened.

## The short version

The fix you approved for [018](018-the-partial-close-can-pay-twice.md) — one
partial close per take-profit level — was **keyed on the wrong thing**. Your own
account disproved it the same afternoon, before the fix had ever run there.

It would have **under-credited a trade by $6.22** and left the app believing it
still held 0.02 lots the broker had already closed. That second part is worse
than the money: it is a phantom holding, the exact failure stage 3 exists to
prevent.

It never reached you. Your database is still at schema version 29 and the fix
is 30, so it would have applied on your next restart. It is corrected now.

## What actually happened on your account

Trade `9f1fd2ea`, the manual order during demo 4, closed like this:

```
16:38:16   TP1   0.01 lots @ 4366.33   $3.04
16:38:17   TP1   0.01 lots @ 4366.53   $3.24
16:38:19   TP1   0.01 lots @ 4366.27   $2.98
```

Three separate closes, at three different prices, 0.03 lots in total — the
whole position — every one a real broker close. They sum to exactly the trade's
realised **$9.26**, and ProfitSync then confirmed that against MT5's own
**$9.27**, adjusting by a penny.

The money was right. The **labels** were not: all three say `TP1`.

## Why my guard would have broken it

Migration 30 made a take-profit level unique per trade:

```sql
UNIQUE(trade_id, reason) WHERE reason GLOB 'TP[0-9]'
```

and the insert uses `INSERT OR IGNORE`. Under that rule, rows two and three are
**silently dropped**:

- realised P&L would read **$3.04** instead of $9.26, and
- `remaining_lots` would stay at **0.02** for a position the broker had closed.

I designed the key around what 018 described — the Python handler and the EA
both reporting one TP hit — and assumed a level could only fire once per trade.
Your account fired it three times, legitimately, within four seconds.

## The correction

Migration 32 changes the key to what actually identifies a close:

```sql
UNIQUE(trade_id, reason, lots_closed, close_price)
```

- **A duplicate report of one close** carries the same level, the same lots and
  the same price. Still refused, so 018's double credit is still fixed — even
  when the two reporters compute slightly different P&L, which they do.
- **Three distinct closes** differ in price. All three are kept.

Old index dropped and recreated, so an install that already applied 30 ends up
identical to a fresh one.

## Why it was found

Not by a test. By reading `vantage_telegram_log` after noticing you had been
sent three `tp1_hit` notifications in three seconds, and following that back
into the database. The three alerts were the visible edge of it.

**The lesson I am taking:** I wrote that key from the bug report's description
rather than from the data, and the data was sitting in your database the whole
time. The tests I wrote all passed, because they tested the behaviour I had
assumed rather than the behaviour your account produces.

## One thing still worth your eye

The three closes were all labelled `TP1` because the take-profit tracking got
confused when you removed the EA and Python reclaimed management mid-trade.
The accounting is now correct either way, but the *labelling* is still wrong —
a scale-out closing in three chunks should read TP1, TP2, TP3, not TP1 three
times. Recorded in [bugs/020](../todo/bugs/020-alerts-were-silently-rejected-by-telegram.md);
not urgent, and not something I would change near the close path without you.
