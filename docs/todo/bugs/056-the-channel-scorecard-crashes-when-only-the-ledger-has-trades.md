# 056 — The channel scorecard raises `UnboundLocalError` when only the ledger has trades

**Status:** found and **FIXED 2026-09-12**, test-first, one mutant killed (the
fix put back).
**Touches money:** not directly — it crashes a read. But the read it crashes is
`recompute_channel_performance`'s input, and that decides `lot_mult` and the
pause flag.
**Severity:** a whole-call exception on a path the History page uses, in a
situation the app deliberately creates.

## The crash

`channels/repo.get_channel_scorecard` merges this node's
`vantage_simulated_trades` with the `consolidated_trades` ledger. Two loops,
one per source. The helpers used by the **second** loop were bound inside the
**first**:

```python
for tg_source, direction, entry, close, pnl, ct, _tid in rows:      # local
    ...
    _session_for_hour, _trade_pts = _analytics_helpers()            # bound HERE
    ...

for tg_source, direction, pnl, ct, tid in ledger_rows:              # ledger
    ...
    sess = _session_for_hour(...)                                   # used HERE
```

With **no local closed trade in the window** and at least one ledger row
carrying a ticket, the first loop never runs, the name is never bound, and the
second loop raises `UnboundLocalError` — taking the entire call with it, not
just that row.

## When that happens for real

A node whose own ledger has been pulled from a peer while it has no closed
trades of its own in the last 30 days:

* a fresh install joined to an existing pair;
* an account switch, where the local trade table is per-account and the ledger
  is not;
* any quiet month on this node while the other one traded.

**This is the second time this function has done this.** The first version —
the same two helpers, not imported into the module at all — is what
`tests/core/test_core_db_channel_scorecard.py` was written for, and its
docstring says it *"crashed the app for real on a demo->live account switch"*.
The import was fixed; the binding moved inside a loop and re-created the same
class of failure on a narrower path.

## The fix

Bind both helpers once, above both loops. That is the whole change. It also
stops re-resolving them on every local row, which is what the old placement
did.

The comment at the fix is three lines rather than the full story, because
`channels/repo.py` sits at 796 of the 800-line ceiling: the first draft of this
fix pushed it to 801 and failed the LOC gate. The rest of the story is here.

Pinned by `tests/db/test_channel_scorecard_ledger_merge.py`: a ledger-only
scorecard returns its row rather than raising, and — separately — that row
still lands in its session bucket, so a fix that merely stopped the exception
without keeping the arithmetic would fail too.

## Found while pinning a different bug

These tests were written to give `docs/todo/bugs/054` a safety net. The crash
turned up on the second test in the file: "a trade only the ledger has is
counted". Nothing in the suite had ever called this function without a local
trade present.
