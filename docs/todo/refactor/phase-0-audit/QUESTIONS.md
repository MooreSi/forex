# Open questions — to align before Phase 1

Every question here blocks or shapes work that follows. Each has a
**recommendation**, so the shortest useful reply is "go with the
recommendations" plus whatever you disagree with. Answered items stay, annotated,
so a later session can see why a call was made.

Context for whoever answers: this is a refactor of a live FOREX trading app.
Phase 0 (an audit, now complete) found that the previous refactor's "Migration
COMPLETE" was wrong in five places and was hiding a live risk-control defect.
Phase 1 onwards moves ~48,000 lines into `backend/` and `frontend/`.

---

## 1. What is the real test baseline? — PARTLY ANSWERED

I can now run the suite here. Three separate problems were making it unusable, two
of them fixed:

**Fixed — the suite read the wall clock.** `dpm_engine.detect_session()` branches on
the current UTC hour and `is_weekly_market_closed()` returns True all weekend, so
every session-gated test passed on a Tuesday and failed on a Saturday with no code
change in between. That alone accounted for **120 failures**: this work happened on
a Saturday, and the historical "1624 passing" baseline was recorded on Tuesday
2026-07-21. `tools/testing/fixed_clock.py` pins both readers to a fixed market-open
instant and is enabled by default in `pyproject.toml`.

**Fixed — `pytest-asyncio` was missing.** Without it every `@pytest.mark.asyncio`
test *fails* rather than skipping, which read as **26 broken tests** instead of one
missing package. Now installed by the session-start hook.

**Not fixed — the suite is polluted and flaky.** With the clock pinned and the
dependencies installed, repeated runs of identical code gave **20, 32, 33, 39, 40,
41 and 58 failures**. The failures cluster in `tests/core/test_scan_messages_*`,
and those files **pass 53/53 when run on their own**. So this is state leaking
between tests, not broken production code.

I tried one plausible cause: 40 of the `fresh_db` variants never reset
`db._rs_cache`/`_rs_cache_ts` on teardown, unlike the canonical one, so a populated
risk-settings cache can outlive its temp database. Patching the 32 of those that
genuinely use `core.database` did **not** change the failure count, and given the
run-to-run variance a single comparison proves nothing either way. I reverted it
rather than ship a 32-file change I cannot show helps.

**So the remaining question is what to do about the flakiness**, because a suite
that varies by 38 failures run-to-run cannot detect a regression from moving code.

- **Recommended: fix the pollution before Phase 1.** Bisect it properly —
  `pytest -p no:randomly --lf`, or run the suite in file-order chunks to find which
  file's state leaks into `test_scan_messages_*`. It is very likely one or two
  module-level globals in `database.py`, which is exactly the state Phase 1 moves,
  so this is work we need done anyway rather than a detour.
- Alternative: record the ~20 stable failures as the baseline and treat anything
  above as noise. Cheap, but it means accepting we cannot tell a real regression
  from flakiness — which is how the previous refactor shipped five false "Done"s.

**ANSWER:**

---

## 2. Is the app running from this repo, or is there a live copy elsewhere?

The old docs repeatedly reference a live app at `/Users/simon/Documents/FOREX`
and a separate `MooreSi/forex` remote, with a standing rule never to touch them.
`core-database-migration/PROGRESS.md:39-52` records a real incident: a browser
preview launch config resolved against the *live* directory, ran the live app for
about thirty seconds, and wrote spurious rows into the live database. This repo
carries an identical `.claude/launch.json`.

I need to know whether that situation still exists, because it changes how
carefully every later phase has to be sequenced.

- **Recommended:** confirm whether `darrenmoore/forex` (this repo) is now the
  only copy, or whether a separate live deployment is still trading. If the
  latter, we need to know how changes reach it before Phase 1 starts.

**ANSWER:**

---

## 3. Do the Telegram-signal position sizes look right now?

Resolved in code, but worth eyes on the outcome.

`suggest_lot_size` existed twice and the copies disagreed: only one applied
Global Parameters > Max Risk per trade % (schema default `1.0`, i.e. on).
Telegram auto-executed signals took the copy without it. Manual orders and bot
commands took the copy with it. Now there is one implementation and the ceiling
applies everywhere.

**Consequence:** positions opened from Telegram signals may be smaller than
before. Fixed-lot overrides are unaffected — `strategy_lot_size` still wins
outright.

- **Recommended:** check what Max Risk per trade % is currently set to, and
  eyeball the next few auto-executed trades against what you would have expected
  previously. If the new sizes look wrong, the setting is the dial — not the code.

**ANSWER:**

---

## 4. The five unwired modules all block on one thing. Wire them, or delete them?

Five extractions were marked Done but never wired, and the inline originals still
run. They share one root cause: each extracted copy builds a partial
`CloseTradeContext`, where the live path uses `engine.py:534
_make_close_trade_ctx()` and its eight collaborators (`tp_cache`,
`scale_out_last_fail`, `tp_safety_net_last_alert`, `on_profit`,
`schedule_profit_sync`, `background_close_commentary`, plus bridge and starting
balance). Wiring any of them as-is would silently drop up to six.

They are `core_mt5_position_sync` (276 LOC), `core_profit_sync.close_full_after_tps`,
and three `core_bot_commands_trading` commands.

- **Recommended: delete the orphans now, re-extract properly in their phase.**
  The inline copies are the live, tested, correct ones. Deleting is zero-risk,
  removes 456 lines of misleading dead code, and stops anyone wiring them by
  mistake. The re-extraction then happens against the real context object.
- Alternative: wire them now by threading the full context through. More
  valuable sooner, but it touches order-closing code, so it needs the demo-account
  gate and your sign-off first.

**ANSWER:**

---

## 5. How much test churn is acceptable in the fixture collapse?

`fresh_db` is defined **119 times in 17 distinct variants**, each poking
`database.py` private state (`_thread_local`, `_db_executor`, `_rs_cache`). That
state moves in Phase 1. Today that is 119 edits; it should be one.

I have added `tests/conftest.py` with the canonical `fresh_db` (the 49-file
majority variant, copied exactly) and a `make_engine` factory. It is additive —
local fixtures shadow it, and the suite behaves identically. I did **not** rewrite
the 119 files, because the variants are not interchangeable and Q1 is unresolved.

- **Recommended:** migrate opportunistically — when a phase touches a test file,
  delete its local copy if it matches the canonical one. Slower, but every change
  is reviewed in context.
- Alternative: one big mechanical sweep of all 119 now. Faster and gets the
  benefit before Phase 1 needs it, but it is a large diff against an untrusted
  baseline, which is precisely the pattern that produced the problems this audit
  found.

**ANSWER:**

---

## 6. What is `frontend/` actually for?

Worth being explicit, because it changes how much effort the split deserves.

NiceGUI renders server-side in the same process and event loop. Splitting
`backend/` from `frontend/` gives a package boundary enforced by import
contracts, not a network boundary — `run.py` still boots one process, and the
frontend is not separately deployable. It is still worth doing: it is what
actually stops views touching the database (14 files do today), and it puts a
real `controllers/` API in place.

- **Recommended: treat it as a code-organisation boundary for now.** Get the
  contracts enforced; revisit a process split only if a real need appears.
- Alternative: the goal is genuinely to replace NiceGUI with a web frontend
  later. Then `controllers/` should be designed as a transport-ready API from the
  start — more upfront work, much cheaper later.

**ANSWER:**

---

## 7. Deferred from the original plan, still unanswered

Carried forward from `backend-foundation/QUESTIONS.md`, all answered in
2026-07-19 with "revisit later". Later has arrived.

| # | Question | Current default |
|---|---|---|
| 6 | Consolidate the 5 separate SQLite files into one? | Keep separate per-engine DBs |
| 8 | What proves a migration is done and safe to cut over? | Undefined app-wide |
| 10 | Money stored as SQLite `REAL` (float) — a real defect per the conventions | Deferred; ripples into UI, sync and alerts |

- **Recommended:** leave 6 and 8 until Phase 2 has proven the pattern on a
  read-only domain, but decide **10** before Phase 8 touches trading — money in
  floats is the kind of bug that shows up as pennies for a year and then a
  material discrepancy.

**ANSWER:**

---

## 8. Two conventions I have been assuming

Cheap to correct now, expensive after 16 domains follow them.

- **Repos return `dict`, never `sqlite3.Row`.** `Row` has no `.get()`, the pages
  call `.get()` everywhere, and an `AttributeError` inside a NiceGUI timer
  callback is *swallowed* — the page silently stops refreshing with no traceback.
- **UI reads stay off the event loop.** `core/database.py:59`'s `to_db_thread`
  exists because synchronous DB calls in `ui.timer` callbacks caused 400-600ms
  stalls on the VPS. The new repos must preserve that dispatch.

- **Recommended:** confirm both. They are already how the migrated engine repos
  behave, so this is ratification rather than a change.

**ANSWER:**
