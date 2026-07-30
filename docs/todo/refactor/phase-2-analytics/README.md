# Phase 2 — analytics

**Status:** in progress
**Started:** 2026-07-27

## Why analytics goes first

It is the only domain with no order path at all. Nothing here can place, modify
or close a trade, so a mistake costs a wrong number on a dashboard rather than a
wrong position. That makes it the right place to prove two things the remaining
eight phases depend on:

1. **The repo pattern against real SQL.** `frontend/pages/history.py` holds the
   ugliest queries in the codebase — 11 inline statements including multi-table
   joins onto `vantage_ladder_legs`, plus two `sqlite3.connect()` calls that open
   *different database files*.
2. **The view/controller split**, on pages nobody's account depends on.

## What has moved so far

```
core/core_db_analytics.py    -> backend/src/services/analytics/read_repo.py
core/core_trade_reporting.py -> backend/src/services/analytics/reporting.py
```

Both verified SELECT-only before moving: no `INSERT`/`UPDATE`/`DELETE`, no call
into `open_trade`/`close_trade`/`place_order`.

## `core_orb_report.py` does NOT belong here

The plan listed it under `analytics/`. That is wrong, and the check caught it:

```python
# core_orb_report.py:338
async def orb_auto_execute(report: dict, bridge: Any, is_active_trader_node: bool) -> None:
```

It **places a genuine EA pending limit order** at the reload level. The
report-building half is read-only analytics; `orb_auto_execute` is a trading
surface and carries the same real-money risk as anything in phase 8.

Moving it wholesale into a phase defined as "no order path" would have quietly
put an order-placing function inside the domain whose entire safety argument is
that it has none. It stays in `core/` until it can be split — the report builder
to `analytics/`, `orb_auto_execute` to `trading/` in phase 8.

Worth noting the plan's other domain assignments were made from module names and
line counts. This one was wrong; others may be. Each module gets the same
read-only check before it moves.

## Still to do

- [x] **Step 1 of draining `history.py`: SQL extracted.** All eight inline
      queries moved to `trade_history_repo.py`; the page's SQL count went 9 -> 1
      and the repo-wide total 240 -> 232. Only the queries moved -- every line of
      shaping stayed where it was, so the page diff is "expression moved" and a
      behaviour change could not hide inside a relocation.
- [x] **Step 2: shaping extracted.** The six pure display helpers moved verbatim
      to `backend/src/controllers/history/controller.py` -- checked for NiceGUI,
      database and engine references first, all six clean. `history.py` is
      1,794 -> 1,644 LOC. Their tests moved with them to
      `tests/controllers/test_history_controller.py`, and coverage went 13 -> 21:
      `parse_reason` and both broker-timestamp helpers had none at all.
- [ ] Step 3: split the `_render_*` functions into separate view files.
- [ ] Step 4: retire the shim and update `frontend/app.py`'s tab registry.
- [x] **Both cross-database reads resolved, and one turned out to be dead.**
      `_query_env_db` — a generic "run this SQL against the other environment's
      database" helper — had **no callers at all**, and `_get_env_db_path` was
      called only by it. Both deleted rather than adapted; building a careful
      adapter for code nothing runs would have been worse than the raw
      `sqlite3.connect()` it replaced.

      The live one, the signal generator's `test_analysis_log`, became
      `signal_lab_repo.py`: a named adapter opened `mode=ro`, returning dicts, and
      degrading to an empty overlay when the file or table is absent (both normal
      on a fresh install). Folding it into `trade_history_repo` would have pointed
      it at the *trading* database, where the table does not exist, and the
      calendar's surrounding `try`/`except` would have swallowed the error and
      rendered a blank overlay — a silent wrong-database read.

      **`history.py` now contains zero raw database access**: no `sqlite3`, no SQL
      string, no `db_module.db()`. 1,644 -> 1,613 LOC.
- [ ] `edge_dashboard.py` (283) and `ai_summary.py` (491). `edge_dashboard`
      already imports no database module, so it is the cleanest template.
- [ ] Split `core_orb_report.py` — report builder here, `orb_auto_execute` deferred
      to phase 8.

## Verification

Full suite after every step: **1996 passed, 0 failed**. All four structure
ratchets green. `python3 -m tools.refactor_audit.check_syntax` runs immediately
after any bulk import rewrite — see below.

### A repeated mistake, now automated away

A bulk `sed` rewrite broke the tree twice in this refactor, both times
identically: a rule written for `from X import Y` applied to
`from X import Y as Z` and produced a double `as`. The second time was *after*
the lesson had been written into the Phase 1b commit message.

`tools/refactor_audit/check_syntax.py` now parses every file in about a second
and names the exact file and line. Writing it down did not work; running it does.
