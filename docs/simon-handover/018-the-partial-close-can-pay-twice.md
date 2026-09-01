# 018 — the partial close can credit the same take-profit twice

**Decision needed:** yes — a small design choice, then I can fix it
**Money:** yes, and it is on the frozen close path
**Found:** 2026-09-01

## What I found

In August we fixed the **full** close: it ran `balance = balance + ?` with no
guard, so recording the same close twice paid out twice. That fix is done and
waiting for your demo (stage1 2/040).

**The partial close has the same shape and was not fixed.** Closing half a
position at TP1 runs:

```
INSERT INTO vantage_partial_closes (...)
UPDATE ... SET realised_pnl = realised_pnl + ?, net_pnl = net_pnl + ?
UPDATE vantage_simulation_account SET balance = balance + ?
```

Nothing makes it idempotent. Fire the same TP1 twice and the account is
credited twice.

## Why the existing guard does not catch it

`partial_close_trade` refuses a trade that is not `open`. But **a partial
leaves the trade open** — that is the whole point of it. So the status check
cannot see a repeat of the same take-profit.

What is supposed to prevent it is the record of which TPs have already fired,
and that record is:

- an **in-memory cache with a 2.5 second lifetime**, never cleared when a
  partial is taken (it happens to work because the handler edits the cached
  copy in place), and
- read *before* the app goes away to talk to the broker, then acted on *after*
  it comes back.

And there are **two independent things that can close the same TP** on the same
trade: the Python strategy handlers, and the EA reporting its own TP hit
through the event path — which never touches that cache at all.

## What it would cost you

Not lots — `remaining_lots` is written as an absolute value, so a repeat sets
the same number rather than closing more of the position. **The money is what
goes wrong**: the P&L is counted twice, in the account balance, in `realised_pnl`
and in `net_pnl`.

That matters beyond the books. The circuit breaker and the daily-loss halt both
read realised P&L, so a double-counted win can cancel a real loss, or a
double-counted loss can trip a halt that should not have fired.

## What I have and have not done

**I have not changed it.** `partial_close_trade` is on the frozen close path,
and unlike the full close this one is not a one-line guard — it needs a
decision from you first.

I have written `tests/trading/test_partial_close_idempotency.py`, which
demonstrates the gap exactly: two tests state the behaviour we want and are
marked as known-failing, one states plainly what happens today (£25 becomes
£50), and one pins the control that any fix must not break — TP1 and TP2 on the
same trade are two legitimate partials, not a repeat.

## The question

**What makes a partial close unique?**

- **"One partial per take-profit level per trade."** Simple, and matches how
  the handlers think. A UNIQUE index on (trade, reason) plus crediting only
  when the insert actually happened. But it forbids two partials at the same
  TP, which the Adaptive Runner ladder might legitimately want.
- **"Only exact repeats within a short window."** Safer against a real
  double-fire, weaker against a slow one.

Tell me which and I will implement it with a migration and tests. It is maybe
an hour's work; the reason it is not done already is that guessing here could
block a legitimate second partial, which is a worse failure than the one it
fixes.
