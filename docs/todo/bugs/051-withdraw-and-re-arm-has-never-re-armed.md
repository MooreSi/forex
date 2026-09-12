# 051 — "Withdraw and re-arm" has never re-armed: the EA cancels it one second later

**Status:** found 2026-09-12 from the live demo database. **Not fixed** — the
fix makes the app place orders it does not place today, and that is the owner's
call however clearly the intent is written down.
**Touches money:** yes. It is the difference between a setup coming back and a
setup being thrown away, on the live-execution engine's order path.
**Severity:** an owner decision taken on 2026-09-10 has been silently inverted
in production since the day it shipped. **Ten for ten.**
**Found:** reading `vantage_pending_orders` and `vantage_telegram_log` for the
limit-orders pack's first live results.

## The decision it inverts

`docs/todo/limit-orders/PROGRESS.md`, decisions log:

> *A failed re-check withdraws and re-arms until the original TTL; it does not
> cancel permanently (owner, 2026-09-10 — **reversed the same day from the
> permanent-cancel default**)*

`broker/repo.mark_pending_order_withdrawn` says the same thing in its own
docstring, and says why:

> *"Deliberately NOT apply_pending_cancelled: that writes status='cancelled'
> AND cancels the signal behind it. Both are final, and a withdrawal is not —
> the setup is exactly what may come back."*

## What actually happens

```
09-11 08:19:40  limit_order_withdrawn      a60448b0
09-11 08:19:40  pending_order_cancelled    a60448b0
09-11 08:29:46  limit_order_withdrawn      54e10770
09-11 08:29:47  pending_order_cancelled    54e10770
09-11 08:31:47  limit_order_withdrawn      d741b511
09-11 08:31:47  pending_order_cancelled    d741b511
```

Every withdrawal is followed by a cancellation within **one second**. Nine
pairs in the log, and every affected row now reads `status='cancelled'` with
`withdraw_count=1` — the withdraw count is the fingerprint proving the
withdrawal landed first and was then overwritten.

**Ten setups were withdrawn. All ten had their signals cancelled. None became a
trade. Not one has ever been re-armed.**

## The mechanism

Four steps, and nothing in them is wrong on its own:

1. Revalidation decides a gate has turned against a resting order. It cancels
   the order at the broker — that is how you pull one off the book — and marks
   the row `status='withdrawn'`.
2. The EA's `CheckPendingOrders` polls and sees an order it was tracking is no
   longer on the book with no matching position. That is exactly what a
   withdrawal looks like from where the EA stands: it cannot tell our
   withdrawal from an expiry or a manual cancel in the terminal, and its own
   docstring says so.
3. It reports `pending_order_cancelled`.
4. `_events._on_pending_order_cancelled` calls `apply_pending_cancelled`
   **unconditionally**. Row → `cancelled`, and the signal behind it → `cancelled`.

The re-arm sweep loads `status IN ('working','withdrawn')`. Once step 4 has
run, the row is not in that set, and the signal it would re-place is cancelled
too. There is no path back.

This is the "two paths to one place, only one defended" shape again —
bugs/014, bugs/019, bugs/046.

## Why nothing looked wrong

Everything reported success. The withdrawal announced itself, the cancellation
announced itself, both alerts sent, all checks stayed green, and the tests for
the re-arm path pass — they exercise the sweep directly and never involve an EA
reporting the withdrawal back. The only place the truth shows is a column
nobody reads: a `vantage_pending_orders` row that is `cancelled` and has
`withdraw_count = 1`.

## What the numbers say about the feature so far

Since it went live on 2026-09-09, seventeen orders have rested:

| outcome | n |
|---|---|
| filled | **1** |
| cancelled after a withdrawal (this bug) | 9 |
| cancelled at the ~60-minute TTL | 4 |
| cancelled otherwise/early | 3 |

Ten of the sixteen cancellations went through this path. How many of them would
have come back is unknowable from here — that is precisely what the re-arm was
built to find out, and it has never once been allowed to run.

## The fix

`_on_pending_order_cancelled` must ignore a cancellation for a row that is
already `withdrawn`: that report is this app's own withdrawal echoing back off
the EA, not the broker or the user cancelling anything.

```python
row = await self._fetch_pending_order(trade_id)
if row and row["status"] == "withdrawn":
    log.debug("[EABridge] pending_order_cancelled for %s is our own withdrawal "
              "echoing back — leaving it withdrawn so the sweep can re-arm it",
              trade_id)
    return
```

Three lines, and it wants a test that goes the whole way round — withdraw,
deliver the EA's cancellation, then sweep and assert the order is re-placed —
because every existing test stops before the echo arrives, which is why this
was never caught.

**It is not applied here.** It makes the app put orders back on the book that
today it drops, on the engine with live execution on, and "restoring what you
asked for" is still a change to order placement. It wants the owner's word and
a demo session, and it is small enough to do inside one.

## Related

* `docs/todo/limit-orders/040-revalidate-before-the-fill.md` — the feature.
* `docs/todo/bugs/039` — cancelling a signal left its order resting: the same
  two surfaces disagreeing, in the other direction.
