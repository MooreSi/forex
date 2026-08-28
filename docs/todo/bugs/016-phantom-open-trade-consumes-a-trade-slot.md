# 016 — A trade that does not exist is holding one of five trade slots

**Status:** found 2026-08-28 evening while working step 1 of
[013](013-ea-stalls-leave-template-trades-unmanaged.md). **FIXED the same evening**
— see the bottom. The live row clears itself on the next app restart.
**Touches money:** yes, indirectly — it permanently reduces how many trades
this account can hold.
**Severity:** live right now, silent, and it has been there for over a day.

## The row

```
trade_id    83aa3510-b632-42
status      open
mt5_ticket  0
strategy    template:Asian Reversal - ATR
tg_source   Reversal Engine
open_time   2026-08-27 17:45:34
```

Still `open` more than 26 hours later.

## It is not real

Checked against the live demo account this evening:

```
GET /positions   ->  {"positions": []}
GET /account     ->  margin 0.0, equity 1323.01, balance 1323.01, profit 0.0
```

No positions, no margin committed, equity equal to balance. There is also no
`vantage_pending_orders` row and no `vantage_ladder_legs` row for this trade.

One honest gap: the bridge exposes no pending-orders endpoint, so a *resting
pending order* could not be ruled out directly. Zero margin, no positions, and
no app-side pending row make it very unlikely, and a pending order that has not
triggered in 26 hours is its own problem.

## Why it costs something

`open_trade()` gates on the count of open rows:

```python
open_count = trade_repo.count_open_trades()
if open_count >= int(rs.get("max_open_trades", 1)):
    raise ValueError(f"Max open trades reached ({rs.get('max_open_trades', 1)})")
```

and `count_open_trades()` is a plain `COUNT(*) ... WHERE status='open'` against
the app's own table. It never asks the broker.

`max_open_trades` is currently **5**. So this row permanently consumes **one
slot in five** — a fifth of the account's trading capacity, gone, with nothing
on screen to explain it. It will keep doing so until someone notices.

It is also noisy: **40 of today's 76 `EA unhealthy` warnings are for this
trade**, which distorts the evidence for 013.

## How it got there, and why nothing cleans it up

An EA Template trade is written as a deliberate placeholder (`mt5_ticket=0`,
`entry_price=0`) at open time. `ea_bridge._promote_leg_fill` is supposed to
turn the first leg that goes live into the row's real ticket and entry. That
promotion is event-driven, so anything that stops the event arriving leaves the
row a ghost.

`core_template_placeholder_repair.py` exists to close exactly this hole by
polling. Its own docstring gives the three cases, and the third is why this row
survives:

> a placeholder with no matching broker deal at all is **left alone** (its legs
> may still be resting as pending orders)

That is a reasonable rule for a placeholder that is minutes old. It has no
upper bound, so a placeholder whose legs never existed is left alone forever.

## Suggested fix (not applied)

Give "left alone" an age limit. A placeholder with no matching broker deal and
no pending order, older than some threshold, is not waiting for anything — it
should be closed as never-filled (P&L zero, not computed from the $0 entry) and
the user told once.

The threshold is a judgement call and belongs to the owner: long enough that a
genuinely resting limit order is never killed, short enough that a slot is not
lost for a day. Whatever it is, this is the close path, so it needs its own
test written first and a demo session.

### The existing tests already draw the line in the right place

Worth knowing before anyone starts, because it looks at first like the fix has
to fight a test. `tests/core/test_template_placeholder_repair.py` has:

```python
def test_leaves_placeholder_alone_when_no_leg_has_filled(fresh_db):
    """Legs may still be resting as pending orders -- nothing to repair, and
    certainly nothing to close."""
```

That asserts exactly the behaviour an age limit would change — but its fixture
inserts the row with `open_time = time.time()`, i.e. a placeholder that is
seconds old. A young placeholder must still be left alone, so **that test keeps
passing unchanged**, and it is the right test to keep: it pins the half of the
rule that must not break.

The fix is therefore additive — a new test for an OLD placeholder with no
broker deal, written first and watched fail. No existing test needs editing,
which is the outcome the golden rules want.

**Do not just delete the row.** Something wrote it, and the same thing will
write another. Understanding why `_promote_leg_fill` never fired for this trade
matters more than clearing one row — though clearing it does get the slot back
in the meantime.

## Also worth deciding separately

`count_open_trades()` counting rows the broker has never heard of is the deeper
issue. Any row that gets stuck `open` for any reason silently reduces trading
capacity. Whether that gate should reconcile against the broker, or whether
keeping it purely local is the safer choice, is a design decision rather than a
bug fix.

---

## Fixed, 2026-08-28

### Why neither existing path could rescue this row

Worth recording, because the first read of this bug ("the repair leaves it
alone forever") was only half the story. The row was stuck in a state **both**
event-driven paths structurally cannot leave:

- `mt5_ticket = 0` — the fill event never arrived, so `_promote_leg_fill`
  never ran.
- `grid_legs_total IS NULL` — the EA's open ack never arrived either. The
  existing `no_fill_expired` close in `_on_grid_leg_cancelled` requires
  `total is not None and cancelled >= total`, and its own comment says
  `total is None` means *"unknown, don't touch"*. So that expiry could never
  fire for this row, however many legs cancelled.

Polling by age is the only thing left that can tell *"never existed"* from
*"still resting"*.

### The change

`core_template_placeholder_repair` gained one branch. When a placeholder has no
live leg **and** no opening deal in 7 days of history **and** is older than the
expiry, it is written off:

```python
await record_close(trade_id, 0.0, "no_fill_expired", ctx)
```

That is the **same call with the same reason** the event-driven path already
makes for a grid whose every leg cancelled unfilled — this is that close
reached by polling instead of by event, not a new kind of close. The reason
string already appears 14 times in the live data.

**It cannot touch a real order.** `record_close` makes no broker call at all —
it records the close in the database — and its `entry_price == 0` guard books
P&L from `mt5_profit` rather than computing one from a zero entry. That guard
is why a real −$15.63 once reported as −$16,086 (trade 76687f1a, 2026-07-29)
cannot happen here. There is no position to close: that is the precondition for
reaching this branch.

### The threshold is yours to move

New Expert Tunable, **Unfilled placeholder expiry**, default **24 hours**
(min 1 hour, max 6 days). Settings > Expert Tunables > Broker reconciliation.

The ceiling is deliberately under the 7-day deal-history lookback: past that,
"no deal" stops meaning "never filled" and starts meaning "too old to see".

24h is the conservative end. Nothing legitimate rests unfilled for a day and
then fills, and a shorter window risks closing a resting order out from under
itself. Lower it if a lost slot for a day is worse than that risk to you.

### What is asserted

Ten tests, written first and watched fail. Beyond the happy path:

- a placeholder just **under** the expiry is still left alone — the boundary
  that protects a genuinely resting order;
- a **live leg** at the broker still wins over age, so an old placeholder whose
  position is open gets adopted rather than abandoned;
- an **opening deal** still wins too, so a leg that opened and closed is
  recorded from the broker's own numbers, not booked as never-filled at zero;
- P&L **and the recorded close price** are both zero — the price matters
  because it is what History displays, and a fabricated one passed every other
  assertion until mutation caught it;
- a row with a real entry price is never expired, whatever its age.

### The live row

Not touched by hand. It clears itself the next time the app runs the repair
poll after a restart, and you will get one Telegram message saying so, naming
the trade and that no position was ever opened and there is no P&L.

## Still open, and separate

`count_open_trades()` counting rows the broker has never heard of remains the
deeper issue — **any** row stuck `open` for any reason silently reduces trading
capacity, and this fix only addresses the placeholder shape of it. Whether that
gate should reconcile against the broker is a design decision, not a bug fix,
and it is still yours.
