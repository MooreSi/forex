# 016 — A trade that does not exist is holding one of five trade slots

**Status:** found 2026-08-28 evening while working step 1 of
[013](013-ea-stalls-leave-template-trades-unmanaged.md). Not fixed.
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
