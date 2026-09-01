# 019 — One bad row in a ledger push drops the sync link, repeatedly

**Status:** fixed 2026-09-01, same change as the tests that found it.
**Found by:** writing `tests/core/test_sync_client_dispatch.py` for
`SyncClient._dispatch` (the cluster-test campaign, `docs/todo/testing/012`).
**Touches money:** no. The consolidated ledger is a reporting table; nothing
here places, closes or sizes anything. It does cost the link over which orders
are forwarded, which is why it is written up rather than just fixed.

## What it was

```python
elif t == MSG_LEDGER_PUSH:
    for row in msg.get("trades", []):
        db_module.record_consolidated_trade(row.get("node_id", ""), row)
```

`consolidated_trades` declares `node_id` and `trade_id` `NOT NULL`, so a row
missing either raises. `_dispatch` is called from inside `async for raw in ws`,
and `_run_loop` catches every exception, logs one line, and reconnects.

So the failure is not "one row skipped". It is:

1. the receive loop ends and the connection drops,
2. **every remaining row in that batch is abandoned**, silently,
3. the 120-second `_ledger_pull_loop` refetches the same batch on reconnect,
4. and the same row does it again.

A permanent reconnect cycle whose only symptom in the log is
`connection error: NOT NULL constraint failed`, with the Mac and the VPS
appearing to be connected between drops.

The same shape was in `MSG_AI_RECOVERED_PUSH` one branch below, where any
failure inside `_apply_ai_recovered_snapshot_row` had the identical effect.

## Why it was there

`MSG_TRADE_CLOSED`, the single-trade path fifteen lines above, has guarded on
both identity columns since it was written:

```python
if node_id and trade.get("trade_id"):
    db_module.record_consolidated_trade(node_id, trade)
```

The bulk path is the same write without the guard. It is the pattern this
codebase keeps finding: **two paths to one place, and only one of them
defended.** The compare-and-set on partial closes, the read failures that
looked like empty answers, and this.

## The fix

Both loops now guard per row: a row that cannot be stored costs that row, is
logged with its id, and the loop continues.

No pre-check on `node_id`/`trade_id` in the bulk path. Mutation testing said
so: with the `try`/`except` in place, deleting the pre-check changed nothing
any test could observe, and an untested branch is worse than no branch. The
single-trade path keeps its guard, because there it is the only protection.

## Has it happened?

Unknown, and probably not. Both senders build their rows from their own
ledgers, so a row without an id would need a schema change or a corrupt row on
the sending side. Worth a look at the VPS logs for `NOT NULL constraint failed`
if the sync link has ever seemed to flap for no reason.
