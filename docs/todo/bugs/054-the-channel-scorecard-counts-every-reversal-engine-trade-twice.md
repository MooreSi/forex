# 054 — The channel scorecard counts 45 Reversal Engine trades twice, and one that never existed

**Status:** found 2026-09-12. **FIXED 2026-09-13 on the owner's instruction**
("Fix 054 and 051"), test-first, four mutants killed. **Shipped without a demo
session, at his direction.**
**Touches money:** yes. `resolution.py` reads this row before every trade: a
paused channel is refused, and an unpaused one has its lot scaled by
`lot_mult`.
**Severity:** the duplicated subset is profitable, so it flatters the channel
in both P&L and win rate — and the inflated win rate sits **half a point** below
the threshold that increases position size by 30%.

## The discrepancy

`channel_performance` against a direct count of the same trades:

| source | stored n | real n | stored P&L | real P&L | stored WR | real WR |
|---|---|---|---|---|---|---|
| Gold Diggers VIP | 68 | 68 | -641.10 | -641.10 | 48.5 | 48.5 |
| GOLD DIGGERS INSTITUTIONAL | 70 | 70 | -1164.90 | -1164.90 | 35.7 | 35.7 |
| **Reversal Engine** | **198** | **152** | **-1833.31** | **-2066.72** | **54.5** | **51.3** |

Every other channel agrees exactly. The Reversal Engine is 46 trades and
$233.41 out.

## Why

`get_channel_scorecard` merges `vantage_simulated_trades` with
`consolidated_trades`, and dedups the two on **`trade_id`**:

```python
local_ids = {r[6] for r in rows}
...
for tg_source, direction, pnl, ct, tid in ledger_rows:
    if tid in local_ids:
        continue
```

The same broker trade reaches the ledger from two places under two different
ids:

* the main close path pushes it as `engine='main'` keyed by the
  **vantage trade_id** (`72f81cd0-9d57-42`);
* the Reversal Engine pushes its own close as `engine='reversal_engine'` keyed
  by its **signal ref** (`RE-36B872`).

Neither id matches the other, so the dedup never fires, and the ticket is
counted twice. Checked by ticket rather than by id:

```
RE ledger rows carrying a ticket:                    46
  ...whose ticket IS ALSO a vantage_simulated_trades row:  45
  ...with mt5_ticket = 0 (RE-4BFC73, +$4.15, "win"):        1
```

**Forty-five duplicates and one phantom.** The ledger query filters
`mt5_ticket IS NOT NULL`, and `0` is not NULL, so a trade that never reached a
broker is counted as a real one.

Zero of the 46 matched a local row by id. The merge is doing exactly what it
was written to do — the docstring explains it exists for *"trades the OTHER
paired node closed"* — and on a single-node install every one of those rows is
a second copy of a trade this node closed itself.

## What it costs

The duplicated 45 sum to **+$229.26**: they are the winners. So the double
count makes the channel look better than it is, twice over —

* net P&L reported as **-$1,833** instead of **-$2,067**;
* win rate reported as **54.5%** instead of **51.3%**.

`recompute_channel_performance`:

```python
elif wr < 55.0:
    lot_mult, auto_pause = 1.0, 0
else:
    lot_mult, auto_pause = 1.3, 0
```

**54.5% is half a point below the line that multiplies this channel's lot size
by 1.3.** The true figure is 3.7 points below it. A slightly better week of
duplicates puts the biggest source of this account's live orders onto 30%
larger positions on the strength of trades counted twice.

Auto-pause is currently disabled (`_CHANNEL_PAUSE_PF = 0.0`), so the other
branch cannot fire today. If it is ever re-enabled it reads the same corrupted
profit factor.

## The fix

Dedup on the broker ticket, not just the id — a ticket already counted from
`vantage_simulated_trades` must not be counted again from the ledger — and
treat `mt5_ticket = 0` as "no ticket", which is what it means everywhere else
in this app.

Both are inside one read-only aggregation. Neither places, closes or modifies
anything.

**Not applied here anyway**, because the output is a sizing input: correcting
it changes `lot_mult` and the pause decision for the channel that produces most
of this account's real orders. It happens to move in the safe direction — the
corrected win rate is further below the 1.3x threshold, not nearer — and it is
still the owner's call, and a small one to take in the same sitting as
bugs/041 and bugs/051.

## Related

* `docs/todo/bugs/049` — the same ledger, a different column, also uncorrected.
* `docs/todo/bugs/031` — the app traded one account and booked to another. Same
  family: two records of one trade that never reconcile.


---

## Fixed, 2026-09-13

Two changes inside `get_channel_scorecard`, both in the read:

* the ledger rows are deduped on the **broker ticket** as well as the trade id,
  so one trade reaching the ledger under two ids is counted once;
* the ledger query is `COALESCE(mt5_ticket, 0) != 0` instead of
  `IS NOT NULL`, so a row with the placeholder ticket `0` is not scored as a
  trade that happened.

**Both halves of the dedup are needed**, and there is a test for the case only
the id catches: a local row carrying `mt5_ticket = 0` puts nothing in the
ticket set, so if the ledger holds the same trade under its own id with a real
ticket, only the id match stops the double count. That mutant survived the
first pass and now does not.

It also keeps counting what the merge exists for: a paired node's trade, with
its own ticket and no local twin, still counts. And the surviving row is the
**local** one — it carries entry and close prices, where a ledger row has none,
so taking the ledger copy instead would quietly flatten `avg_pts` and
`payoff_rr` for the whole channel.

The two tests written on 2026-09-12 asserting the broken answers were flipped
to the correct ones. They were written that way deliberately, each carrying a
message saying what to change when the fix came; this is that change, not a
test edited to make something pass.

**What the owner will see:** the Reversal Engine's row recomputes to roughly
51.3% and -$2,067 from 54.5% and -$1,833. That is further below the 55% line
that multiplies its lot size by 1.3, so the correction moves sizing in the
conservative direction.