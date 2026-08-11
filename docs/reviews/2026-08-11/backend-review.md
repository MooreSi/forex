# Backend architecture review — 2026-08-11

Scope: layering, controller thinness, the runtime facade, dead code, file
sizes, cross-engine duplication, import cycles, event-loop hygiene, threading,
exception-swallowing. Read-only: nothing was run except `python -m
tools.refactor_audit.import_contracts --check` (allowed), `git log/show`, and
greps/line counts. No app, no tests, no MT5. Line numbers are as of today's
working tree (HEAD `8e45983`).

## Summary + verdict

The three headline remediation claims from the 2026-08-08 review are **real,
not cosmetic**: the ~3,384 lines of dead per-engine `database.py` clones are
deleted (commit `da117b6`, 2026-08-10) and a brand-new *fail-closed*
module-level orphan gate (`tools/refactor_audit/orphan_modules.py`) now guards
against recurrence; `backend/src/db/database.py` is down from 1,251 to **456
lines** with schema/migrations/backfills genuinely relocated to
`backend/migrations/` (commit `2d17b94`); and `utils/news_calendar.py` was
rewritten around a background refresher thread so the getter is a pure cache
read — including the None-caching bug fix, explicitly documented at
`news_calendar.py:27-33`.

The verdict: **the layering and gate architecture is genuinely sound — but the
fix was applied to the named instance, not always to the pattern.** The exact
blocking-fetch-on-the-event-loop disease fixed in `news_calendar.py` survives,
bug-for-bug (inline urllib *and* the failure-not-cached TTL defeat), in its
sibling `test_signal/news_filter.py`, on the live cycle of two engines. The
risk↔cluster import cycle, the upward re-export hub, the cross-engine
indicator borrowing, the dead self-healer patterns, and the unsupervised
runtime tasks are all still there. What was fixed was fixed well; what wasn't
fixed wasn't touched.

## Previous-findings verification

| 2026-08-08 finding | Status | Evidence |
|---|---|---|
| C3 dead per-engine `database.py` clones (~2,800 L) | **FIXED** | All three files gone (`services/{breakout_signal,reversal_engine,test_signal}/database.py` do not exist); commit `da117b6` "Delete the three dead per-engine database.py clones (3,384 LOC)", including re-pointing the characterization tests |
| C3b orphan gate scans a deleted directory | **FIXED** | New `tools/refactor_audit/orphan_modules.py` — AST reachability from 5 named entrypoints, **fails closed** on missing roots (docstring lines 16-20), wired into `tools/checks.py:54-55`; allowlist is an explicit debt ledger (`orphan_module_allowlist.json`, 6 entries ≈1,082 LOC, each with owner-decision reason). Old `orphan_detector.py` kept only as a helper library |
| C4 blocking news fetch on the event loop + None-not-cached | **FIXED (for this file)** | `utils/news_calendar.py:99-112` getter is lock-guarded cache read only; daemon thread `news-calendar-refresh` (`:71-90`) does all fetching; None is a cached value (`:65-67`); started at boot `backend/src/app.py:343`. **But see NEW-H1 — the identical bug lives on in `test_signal/news_filter.py`** |
| db/database.py 1,251 L god file / split claim | **FIXED, better than claimed** | Now **456 lines** (`backend/src/db/database.py`); DDL/migrations/backfills moved to `backend/migrations/` (schema_sql.py 515 L, registry.py 322 L, backfills.py 182 L, commit `2d17b94`); migrations are a numbered fail-closed registry with `_verify_critical_schema` (`database.py:243-244`) |
| H5 upward re-export hub (~100 names from 17 service repos) | **PARTIAL** | Hub shrunk but intact: `database.py:270-456` (~202 lines) still imports from risk, cluster, channels, telegram, ai, notifications, positions, broker — bottom layer still executes half the service tree on import. The `_ANALYTICS_LAZY` workaround survives (`:333`) |
| H4 weakest-configured main DB connection | **PARTIAL** | `PRAGMA busy_timeout=5000` added with a review-citing comment (`database.py:174-177`); `journal_mode=WAL` now in the base DDL (`backend/migrations/schema_sql.py:9`). Still no `timeout=` on `sqlite3.connect` (`database.py:170`) and repos still reach into `database._DB_PATH` for read-only connects |
| H7 risk↔cluster import cycle | **NOT FIXED** | 8 imports each way, unchanged: `risk/expert_params.py:333,342`, `risk/risk_settings_repo.py:84,98`, `risk/schedule.py:163,172`, `risk/strategy_params.py:238,247` → cluster.sync; `cluster/sync/client.py:450,464`, `cluster/sync/server.py:575-606`, `cluster/sync_repo.py:25-26` → risk |
| H7b trading↔broker cycle | **NOT FIXED** (mild) | trading→broker 15 imports; back-edge is a single import: `broker/history_import.py:21` → `trading.fees_sizing`. positions↔trading and telegram↔trading back-edges also remain |
| H3 cross-engine indicator borrowing | **NOT FIXED** | `breakout_signal/signal_generator.py:23` still imports ten indicators from `test_signal.signal_generator`; `breakout_signal_service.py:586` still lazily imports `test_signal.market_context` |
| H6 self-healer patterns match nothing; no task supervision | **NOT FIXED** | `health/self_healer.py:57` still greps for `Exception in monitor loop|Error in position monitor|monitor.*crash`; the only real log line is `"Monitor loop error: %s"` (`positions/monitor_cycle.py:229`) — none of the three patterns match it. Zero `add_done_callback` on the 13 tasks at `runtime.py:285-297`; `shutdown()` still cancels without awaiting |
| C2 `record_close` after failed broker close | **NOT FIXED** | `positions/monitor_loop.py:121-129`: on `{"error"}` or exception, `record_close(..., "profit_close_target")` still runs unconditionally with a synthetic price. (Frozen close path — presumably awaiting Simon sign-off, but nothing marks it as such at the site) |
| C1 unchecked `modify_order` at ~14 sites | **NOT FIXED** | e.g. `positions/handle_scale_out.py:111` still discards the result, then writes `set_stop_loss_be` and sends the Telegram alert. No shared checked-modify helper exists in `services/broker/` |
| C5 divergent tunables | **NOT FIXED** | `risk/governor.py:136` reads the tunable, `:209-212` still hardcodes `same_dir >= 2` / "directional cap is 2"; `trading/instant_entry.py:348` still hardcodes the six TP offsets |
| M5 stale `_conn()` doc paragraph | **NOT FIXED** | `docs/system/rules/30-architecture.md:167-170` still describes the non-nesting per-engine `_conn()` — which now describes *deleted* files; the enforcement table (`:179`) still points "Dead extractions" at the vacuous `orphan_detector`, not `orphan_modules` |
| Layer contracts hold | **STILL HOLDS** | `import_contracts --check` today: all four zero contracts enforced at zero; `frontend-reaches-the-backend-through-controllers` baseline ratcheted **59→50**; nicegui-in-backend 2, utils-upward 3 (both baselined, unchanged) |
| Controllers thin | **STILL HOLDS** | Largest `controllers/sync_controller.py` 166 L; 892 L total across 7 flat controllers |

## New findings

### High

**NEW-H1. The news_calendar fix was not propagated to its sibling: blocking
urllib on the event loop survives in `test_signal/news_filter.py`, with the
same TTL-defeat bug.**
`news_filter._fetch_calendar()` (`backend/src/services/test_signal/news_filter.py:39-66`)
does `urllib.request.urlopen(req, timeout=8, ...)` inline. Its callers are the
live async cycles: `test_signal/test_signal_generate.py:127 _run_cycle()` and
`breakout_signal/breakout_signal_service.py:325 _run_cycle()` (both `async
def`), plus `breakout_signal_velocity.py:61`, via
`test_signal/signal_generator.py:366 is_news_window()`. Worse, the failure
path (`news_filter.py:64-66`) returns without setting `_CACHE`/`_CACHE_TS`, so
while the feed is down **every cycle refetches, blocking the loop up to 8 s
each time** — bit-for-bit the two bugs the news_calendar rewrite documents
fixing (`news_calendar.py:27-33`). This loop also runs the 50 ms TP-ladder
poll and MT5 sync. Fix is small: route `is_high_impact_window` through the
already-fixed `news_calendar` refresher, or copy its thread+cache-None pattern.

**NEW-H2. `runtime.py` is still 13 unsupervised `create_task`s with a
cancel-and-forget shutdown.** Unchanged from H6/L3 and worth restating as the
single biggest operational gap in backend scope: a dead monitor task means no
TP/SL management on live positions with zero log line, and the self-healer
that is supposed to catch it greps for messages nobody logs
(`self_healer.py:57` vs `monitor_cycle.py:229`). A one-line `add_done_callback`
that logs at ERROR and restarts (or at least alerts) would close it.

### Medium

**NEW-M1. Engine twin-file duplication is untouched.** breakout_signal and
test_signal still carry parallel `adaptive_params.py`, `claude_reviewer.py`,
`*_velocity.py`, `panel_data.py`, `ml_engine.py`, `signal_generator.py`; 11
`get_perf_by_*` GROUP-BY templates across the three `*_repo.py` files; three
divergent `get_ml_metrics` (`breakout_signal/ml_engine.py:561`,
`reversal_engine/ml_engine.py:467`, `test_signal/ml_engine.py:498`). One
arithmetic fix still fans out to 6-9 places. Deleting the dead clones halved
the *dead* duplication; the *live* duplication is the same size as before.

**NEW-M2. Ratchet baselines were not tightened after the wins, and carry
stale entries.** `tools/refactor_audit/structure_baseline.json` still records
`backend/src/db/database.py: 1251` (actual 456) — the file could regrow by
~800 lines before the loc gate notices — and its `transaction` section still
lists the *deleted* `reversal_engine/database.py` and `test_signal/database.py`.
Shrink-only ratchets only ratchet if you re-baseline after shrinking; run
`--update-baseline` while the totals are down.

**NEW-M3. `cluster/remote/server.py` (1,196 L) god module unchanged**, still
the largest backend file after runtime, still mixing token store, licence
issuance, update-ZIP shipping, rate limiting, UDP beacons, TLS lifecycle, and
dispatch, with module-level mutable session state. `cluster/remote/client.py:323`
also does an inline `urlopen(..., timeout=0.5)` health probe inside the
async status-message builder — small, but on the loop.

### Low

**NEW-L1.** `frontend-reaches-the-backend-through-controllers` shrank 59→50
but 50 direct service imports remain the largest baselined debt; frontend page
sizes are essentially frozen (settings.py 3,112 → 3,112; app.py 1,633 → 1,605).
Backend work moved; the frontend restructure has not (frontend reviewer's
scope, noted for the cross-reference).
**NEW-L2.** `test_signal/ml_engine.py:489 _compute_mcc` still has zero
references anywhere (function-level dead code the module-level gate can't see).
**NEW-L3.** `utils/news_calendar.py:146` still imports
`services.broker.mt5_client` from utils (1 of the 3 baselined upward
violations) — the new refresher design would let this move into a broker-side
provider callback and retire a baseline slot cheaply.

## Measured numbers

- Backend: 260 .py files, 55,281 lines. Frontend: 38 files, 18,434 lines.
- Files over the 800-line rule — backend 6: `runtime.py` 1,310;
  `cluster/remote/server.py` 1,196; `cluster/sync/server.py` 1,073;
  `cluster/remote/client.py` 920; `cluster/sync/client.py` 867;
  `reversal_engine/reversal_engine_repo.py` 809. Frontend 8: `settings.py`
  3,112; `app.py` 1,605; `history.py` 1,415; `ai_trade_analysis.py` 1,250;
  `test_panel.py` 1,245; `breakout_panel.py` 918; `chart.py` 839;
  `reversal_panel.py` 803. Root: `mt5_bridge.py` 1,335. All under the
  shrink-only loc ratchet; none new since 08-08, three shrank slightly.
- `backend/src/db/` total is now 851 lines across 8 files (was a 1,251-line
  monolith); `backend/migrations/` is 1,019 lines.
- Controllers: 7 files, 892 lines total, max 166 (`sync_controller.py`).
- `except Exception` in `backend/src`: **696** (was 718); immediately followed
  by `pass`: **146** (was 161); truly bare `except:`: **0**.
- `time.sleep(` in `backend/src`: **0** matches. Background threads: exactly
  two created in backend (`mt5_native.py:105` reconnect — the pre-existing H8
  race note stands — and `news_calendar.py:87` refresher) plus the dedicated
  `db-worker` executor thread (`database.py:36`).
- Import contracts today: 4 contracts at zero, `frontend→controllers` 50/50
  baseline (was 59), `no-nicegui-in-backend` 2, `utils-upward` 3.
- Cross-service back-edges (import counts): risk→cluster 8 / cluster→risk 8;
  trading→broker 15 / broker→trading 1; positions→trading 15 /
  trading→positions present; broker→telegram 8 / telegram→broker 2.

## What is genuinely healthy

- **The gate culture is now self-correcting.** The 08-08 review's worst meta
  finding — a guardrail passing vacuously — was answered with a *fail-closed*
  replacement whose docstring names the failure mode it prevents, and whose
  allowlist entries are dated debt records with owner-decision reasons
  (`orphan_module_allowlist.json`). That is the right instinct, executed well.
- The clone deletion was done properly: characterization tests re-pointed, a
  borrowed test row-builder inlined, coverage floors honestly *lowered* to
  match, stale allowlist entries dropped (commit `da117b6` message).
- The `db/` package is now legible: connection + nesting-depth transaction +
  cache-invalidator registry in 456 lines, schema evolution in a numbered
  fail-closed registry under `backend/migrations/` with a boot-time critical-
  schema verification. Comments carry the incident history (the 2026-07-21
  demo/live-switch bug) — this is maintainable code.
- Layering holds under an enforced checker, controllers are genuinely thin,
  and the facade is delegation not logic. `runtime.py`'s 1,310 lines are loops
  and context builders, not a god class.
- Zero `time.sleep` and zero bare `except:` in 55K lines of backend.

## Honest opinion

This is no longer rules-on-paper: when this team fixes something, the fix is
thorough, documented, and gated against recurrence. But the remediation pattern
is *instance-based, not pattern-based* — `news_calendar.py` was rebuilt while
`news_filter.py`, ten lines of grep away with the same two bugs on the same
event loop, was left running; `busy_timeout` was added where the review pointed
while `record_close`-after-failed-close and the unchecked `modify_order` sites
(the two money-path items in backend scope) are byte-identical to 08-08. The
next six months are safe if each fix session ends with "grep for the pattern,
not the file", the ratchet baselines get re-tightened after every win, and the
two deferred money-path items get their Simon-gated demo session soon — they
are the oldest confirmed-loss-class findings still open. The refactor is
cosmetic nowhere I looked; it is simply incomplete in exactly the places the
08-08 report said needed owner sign-off, and nothing at those sites records
that they are consciously deferred rather than forgotten.
