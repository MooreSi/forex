# 039 — "Signal cancelled" left the broker order live

**Status:** FIXED 2026-09-09, test-first, five mutants killed. Found running
demo 7 on the demo account.
**Money:** yes. A "cancelled" order kept a trade slot and could still fill.

## What happened

A limit order was placed from Trading > Limit Order and then cancelled from
Pending Signals. The UI said **"Signal cancelled"**. The order was still
resting at the broker, and the database said so plainly:

```
vantage_pending_orders   trade_id=a401553e  signal_id=4fd3a43f
                         ea_ticket=1973407311  price=4300.0  status='working'
vantage_signals          signal_id=4fd3a43f  status='cancelled'
```

The EA log has the placement and **no withdrawal**:

```
20:32:52 [EABridge] pending order placed BUY ticket=1973407311
                    strategy=limit_runner price=4300.0 expiresMin=240.0
```

## Cause

`runtime.cancel_signal` called `signals/repo.cancel_signal`, which is one
`UPDATE` on `vantage_signals`. Nothing ever asked the EA to withdraw the order.

## Why it is a money problem

* Since [026](026-resting-orders-consumed-no-trade-slot.md) a resting order
  **consumes a trade slot**, so a cancelled-but-live order blocks one for its
  full `expiresMin=240` — four hours.
* It can still **fill**. The operator believes they called the trade off and
  can be opened into it anyway.
* **There was no other way out.** No controller and no UI exposed a cancel for
  a working pending order, so once placed it could not be withdrawn from the
  app at all.

## Fixed

New `services/signals/cancellation.py`. It cancels the signal, finds any
working pending order for that `signal_id`, and asks the EA to withdraw it.
The EA call lives in a service rather than the repo because repos hold SQL and
services decide (rules/30-architecture).

Three deliberate choices:

* **The signal is always cancelled**, even if the withdrawal fails. The user
  asked for a cancel; refusing it because the EA is unreachable would leave
  both the signal and the order live.
* **A refused withdrawal leaves the row `working`.** It is still consuming a
  slot and can still fill, so marking it resolved would hide a live order.
  Logged as `STILL LIVE` at WARNING.
* **A row with no broker ticket is skipped, not guessed at** — the same rule
  `resting_revalidation` already follows.

## Mutants

| Mutant | Killed by |
|---|---|
| withdrawal skipped entirely | 2 tests |
| zero ticket not guarded | 1 |
| refused withdrawal marked resolved | 1 |
| runtime rebound to the repo | 2 |
| **the `signal_id` filter removed** | 2 — **only after new tests were added** |

That last one **survived the first pass**, because every test stubbed
`_working_orders_for` — the function that does the filtering. A mutant
cancelling *every* signal's orders passed the whole file. Three tests now drive
the real function and stub only the repo beneath it.

## Note on the line ceiling

`runtime.py` is in `structure_baseline.json` and is shrink-only. The first
version of the wiring added four lines. It was restructured to a module-level
binding so the file is back at exactly 1513 lines; no baseline was raised.
