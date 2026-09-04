# 025 — A `trade_closed` with no price was booked as an exit at $0.00

**Status:** fixed 2026-09-04, test-first. The GUARD is verified by tests; the
LIVE ROW it already corrupted is not repaired — see Sign-off needed.
**Found:** live, 2026-09-04, ticket 1935433548, reported by the owner after a
bridge restart produced a Telegram close for a trade that never appears in
Closed Trades.
**Touches money:** yes — it wrote a fabricated loss to `net_pnl`,
`realised_pnl` and `vantage_simulation_account.balance`, and fed it to the
halt guards.
**Severity:** one fake -$44,783.50 loss per orphaned ticket, each capable of
halting trading for the day.

## What was seen

```
XAUUSD Trade Closed ❌
Closed While Disconnected
Direction: BUY  |  Lots: 0.1  |  Held: ?
MT5 Ticket: 1935433548
Entry: $4478.35  →  Exit: $0.00
Profit: $-44783.50
Total pips: -44783.5
Risk:Reward: -893.88R
```

The trade never appeared in Closed Trades.

## Root cause

On "hello" the app pushes every open EA-managed row back to the EA
(`_restore.restore_trade`, rows from `broker_repo.fetch_open_ea_managed_trades`).
`HandleRestoreTrade` could not select ticket 1935433548 as a position, so it
replied:

```json
{"type":"trade_closed","trade_id":"...","ticket":1935433548,
 "reason":"closed_while_disconnected"}
```

with **no `close_price`**. It is the only sender that omits one — every real
close goes through `ReportTradeClosed`, which always sends it.

`_events._on_trade_closed` read the absence as `float(msg.get("close_price", 0))`
= 0.0 and passed it to `record_close`, which has an `entry_price == 0` guard
(the 2026-07-29 -$16,086 incident) but **no `close_price == 0` guard**. With
entry 4478.35 and exit 0.00 at 0.1 lots it computed `(0 - 4478.35) x 0.1 x 100`
= -$44,783.50, wrote it, credited the simulated balance with it, and handed it
to `apply_giveback_guard_on_close` and the daily-loss ceiling — both of which
replay `net_pnl` from closed rows (`read_repo.closed_pnls_since`) and halt
trading for the day.

The absence from Closed Trades is itself the evidence: that table is built
from MT5 **deal history** (`_trade_table.py` → `get_deal_history`), so a row
the app closed with no broker deal behind it cannot appear. The broker had no
closing deal for the ticket at all.

## What changed

`_on_trade_closed` now treats a close with no usable price as an OBSERVATION
that the EA cannot see the ticket, not a settled exit. New
`_broker_exit_price()` asks the broker (`get_position_history`), keeps deals
with `entry != 0` (an opening deal read as a close would book the trade shut
at its own entry), and takes the LAST exit — a staged exit leaves one deal per
portion. With no closing deal it records nothing, leaves the row open, and
sends an `ea_close_unverified` alert naming the ticket. A close that carries a
price is untouched and never consults the broker.

## Verification

`tests/services/broker/test_ea_close_without_a_price.py` — 13 cases, run red
first (9 failed on `record_close` being called with `0.0`; the 2 controls
passed, which is what proves the normal path still closes).

## Sign-off needed

1. **The `close_price == 0` guard inside `record_close` is NOT done.** It is
   the frozen close path (CLAUDE.md rule 4) and needs owner sign-off plus a
   demo session. The bridge-side guard above stops the reported incident
   before `record_close` sees it; the second guard is defence in depth.
2. **The live row for ticket 1935433548 is still wrong** — status closed,
   `close_price` 0, ~-$44,783 in `net_pnl`/`realised_pnl` and debited from
   `vantage_simulation_account`. Repairing it, and checking whether
   `trade_pause_until` / `risk_halt_reason` were set off the back of it, is a
   separate decision.
