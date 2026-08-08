# Backend review — 2026-08-08

Scope: `backend/` (252 files, ~56,200 lines) of the live-money MT5 trading app.
Read-only review: no code was modified, nothing was run that touches MT5, the
broker, or the databases. Line numbers are as of today's working tree.

## Summary

The layering story holds up: **all four zero-enforced import contracts verify
clean by direct grep**, controllers are genuinely thin (largest 166 lines), and
`runtime.py` is a real facade of one-to-three-line delegating methods rather
than a god class. The ratchet/gate tooling is unusually good for a codebase of
this size.

The serious problems are not in the layers — they are in the money paths and
in duplication:

1. **`modify_order()` results are unchecked at ~14 SL-move sites.** The broker
   reports rejection as a returned `{"error": ...}` dict, and only
   `positions/safety_net.py` checks it — a fix written after a confirmed live
   loss (ticket 1543412796) that was never propagated. Every strategy handler
   still records "SL moved to break-even" in the DB and alerts Telegram even
   when MT5 rejected the move.
2. **`record_close` can run when the broker close failed**
   (`positions/monitor_loop.py:128`) — DB says closed, position still open.
3. **~2,800 lines of dead code**: the three per-engine `database.py` modules
   (~2,171 lines, zero production imports, pinned alive only by
   characterization tests) plus 4 orphaned modules (~642 lines) that the
   orphan detector cannot see because it still scans the deleted
   `forex_trader/core/` directory — the exact "guardrail that prints all good"
   failure CLAUDE.md warns about.
4. **A blocking news-calendar fetch runs on the asyncio event loop** from the
   live-execution paths of all three engines, and a cache bug makes it re-run
   the network calls on *every* cycle whenever no upcoming event exists.
5. **Tunables that silently don't apply**: the directional cap and the
   Conservative-Trial SL/TP set each exist twice — once as an editable tunable
   and once as a hardcoded literal on a different code path.

## How this review was done

- Read `CLAUDE.md`, `docs/system/rules/30-architecture.md`, and the
  `tools/refactor_audit/` gate sources and baselines.
- Verified the four zero-enforced contracts by grepping imports directly
  (frontend→db, controllers→db/repo, services→controllers, services→nicegui),
  and re-measured the three baselined contracts.
- Built an AST-based import graph over `backend/`, `frontend/`, `tools/`,
  `tests/`, and root scripts to find modules nothing imports, then confirmed
  each candidate with string greps (to catch dynamic/lazy imports).
- Generated a cross-service dependency matrix from `from backend.src.services.X`
  imports.
- Outlined and read the god files (`runtime.py`, `db/database.py`, both cluster
  servers) and the close path.
- Three parallel deep-dive passes (signal-engine duplication; error handling on
  broker/trading/positions paths; concurrency + config sprawl), each of whose
  headline claims I independently re-verified against the source
  (`governor.py:136` vs `:209`, `news_calendar.py:49`,
  `monitor_loop.py:122-128`, `handle_scale_out.py:111-113`,
  `runtime.py:713-722`, zero production imports of the engine `database.py`
  modules).
- Nothing was executed except read-only greps and one read-only
  `python` AST/import-graph script. No app code, no tests, no MT5.

### Contract verification results

| Claim | Result |
|---|---|
| `frontend` never imports `backend.src.db` | **Holds** — zero matches |
| `controllers` never import `backend.src.db` or a service repo | **Holds** — only a docstring mention in `controllers/__init__.py:7` |
| `services` never import a controller | **Holds** — zero matches |
| `services` never import `nicegui` | One baselined function-local import: `services/telegram/bot_infra.py:45` (app shutdown; covered by the `no-nicegui-in-the-backend` baseline of 2) |
| `utils/`/`config/` import nothing above them | 3 baselined violations: `utils/news_calendar.py:81` (→ broker), `config/licence/guard.py:180,287-288` (→ cluster.remote) — matches the shrink-only baseline of 3 |
| `frontend-reaches-the-backend-through-controllers` | 41 direct service imports across 17 files — under the baseline of 59, shrinking as intended |
| Controllers thin | Largest is `sync_controller.py` at 166 lines; all flat `*_controller.py`; `controller_loc` ceiling 200 respected |

---

## Findings

### Critical

**C1. `bridge.modify_order()` rejection is ignored at ~14 SL-move sites; DB and
alerts claim protection that doesn't exist.**
`mt5_bridge.py:898` returns `{"error": "Modify failed: <retcode>"}` on broker
rejection — no exception. The only call site that checks is
`backend/src/services/positions/safety_net.py:150-167`, whose comment records
the confirmed live incident: ticket 1543412796 was marked `sl_moved_to_be=1`
at 4157.08 while MT5 closed the position at the original, unmoved 4150.00 stop
for a real loss. Every other site still writes the DB (and in three cases sends
the "SL moved to BE" Telegram alert) regardless of the result:
- `positions/handle_scale_out.py:111-117` (writes flag + sends alert)
- `positions/handle_protected_scale.py:78-82` (writes + alert)
- `positions/handle_no_sl_scale.py:164-168` (writes + alert)
- `positions/tp_ladder.py:179-181` (`set_stop_loss_be_flag` unconditional)
- `positions/handle_be_runner.py:83-87` (`lock_sl_with_marker` unconditional)
- `positions/handle_trail_stop.py:109-110`, `handle_conservative.py:128-130,152-153`,
  `handle_scalp_runner.py:148-150,172-173`
- `positions/handle_conservative_trial.py:130-134` — catches the exception but
  `set_stop_loss_be` sits *outside* the `try`, so it runs even on failure
- `trading/ai_signal_fallback.py:227-228`, `trading/update_signal.py:111-115`,
  `trading/open_from_signal.py:114,147,185,207,231,254,280`
Because nothing checks the result, the doomed modify is also silently retried
every monitor cycle with no backoff — the same unbounded-retry class that
`safety_net.py:119-121` documents fixing for its own path.
By contrast, `partial_close` results **are** checked at all ~10 sites
(`tp_ladder.py:134-140`, `handle_scale_out.py:85`, etc.), proving the codebase
knows the pattern.

**C2. `record_close` runs even when the broker close failed.**
`backend/src/services/positions/monitor_loop.py:121-128`: the profit-target
close calls `bridge.close_position()`, and if it returns `{"error"}` or raises,
execution falls through to `record_close(trade_id, close_price, "profit_close_target", ctx)`
at line 128 unconditionally — the DB marks the trade closed at a synthetic
price while the live MT5 position remains open. The correct pattern exists 100
lines away in `trading/close_trade.py:113-121` (raises on `error` and on
`success is False`).
Related: `trading/close_trade.py:294-312` — a ladder leg whose close is
rejected is `continue`d, then `apply_ladder_close` records the parent closed
including the lots of legs still genuinely open at the broker.

**C3. ~2,171 lines of dead legacy data-access modules shadow the live ones —
the audited "~3,000 orphaned lines" failure mode has recurred.**
`services/breakout_signal/database.py` (698 L), `services/reversal_engine/database.py`
(752 L), `services/test_signal/database.py` (721 L) have **zero production
imports** (verified by AST import graph and string grep); production uses the
`*_repo.py` twins, which are ~90% structural clones. Only five characterization
test files keep them alive. A reviewer reading `breakout_signal/database.py:277
close_signal` is reading code that never runs, while the *live* copy carries a
knowingly-preserved balance double-counting bug, admitted at
`breakout_signal_repo.py:1-15` ("INCLUDING the known close_signal balance
double-counting bug… deliberately preserved here, not fixed").
On top of that, four whole modules are orphaned (~642 lines):
`services/channels/rule_generator.py` (275 L), `services/breakout_signal/backtest.py`
(226 L, only self-referenced in its own docstring), `config/licence/client.py`
(90 L), `services/test_signal/auth.py` (51 L).
And the tool that should catch this can't: `tools/refactor_audit/orphan_detector.py:31-34`
still globs `forex_trader/core/` — a deleted directory — and its own comment
admits every core-scoped check is "vacuously green". That is precisely the
guardrail failure CLAUDE.md's closing paragraph describes.

**C4. Blocking HTTP on the asyncio event loop in live-execution paths, with a
cache bug that defeats the TTL.**
`utils/news_calendar.py:41-55 get_news_proximity_norm()` is synchronous; on
cache miss it tries three sources in sequence, two via blocking
`urllib.request.urlopen(..., timeout=5)` (`news_calendar.py:140,180`) — up to
~15 s of event-loop freeze. Verified at line 49: the result is only cached when
`_cache_next_mins is not None`, so whenever no upcoming high-impact event
exists (most of the time), **every call refetches over the network**. Callers,
all `async` with no `to_thread` wrapper:
`reversal_engine/reversal_engine_live_execute.py:109` (live execution),
`reversal_engine/reversal_engine_service.py:327-328`,
`breakout_signal/breakout_signal_service.py:592`,
`test_signal/test_signal_generate.py:404`. The same loop runs the 50 ms
TP-ladder poll (`runtime.py:656-670`) and MT5 position sync — this is a highly
plausible cause of the stalls `utils/loop_monitor.py` exists to detect.

**C5. Tunables that silently don't apply — two divergent copies on live paths.**
- Directional cap: `services/risk/governor.py:136` reads
  `expert_params.get("max_unprotected_trades")`, but `governor.py:207-214`
  (the `rg_size_and_check` path) hardcodes `if same_dir >= 2` with the literal
  in the user-facing message ("directional cap is 2"). Editing the tunable
  changes one path and not the other.
- Conservative-Trial: `trading/instant_entry.py:344` hardcodes
  `sl_risk_usd = 100.0` and `:348` hardcodes the six TP offsets
  `(5.0, 10.0, 14.0, 20.0, 27.0, 35.0)`, duplicating
  `services/risk/strategy_params.py:94-105` exactly; the
  `open_from_signal.py:174` path reads the tunable, the IME path ignores it.

### High

**H1. Bridge-offline is indistinguishable from "no positions"/"no data" at
guard-critical call sites.**
- `broker/mt5_client.py:273-282 get_positions()` returns `[]` on any failure.
  `broker/position_sync.py:108-112` guards this with a health check;
  `runtime.py:713-722 _close_full_after_tps` does not — both the empty-list
  and exception paths yield `residual = None` at `log.debug`, silently
  disabling the residual-position safety net that is the function's whole
  purpose.
- `broker/position_sync.py:239-240`: unlogged
  `except Exception: all_known_tickets = set()` — if the known-ticket read
  fails, every live MT5 position looks untracked and is re-imported as a new
  trade row (`:257-266`).
- `trading/close_trade.py:77-84`: `get_account()` failure silently substitutes
  the internal simulation ledger balance — which the file itself
  (`close_trade.py:162-167`) warns "can and does drift" — and that balance
  feeds the peak-balance watermark and drawdown circuit breaker
  (`record_close` at `:168-178`, `:229-238`, both swallowing at `log.debug`).
- `broker/untracked.py:27-28` and `broker/mt5_native.py:329,335,341`: bare
  `except Exception: return []/None`, the latter three with no logging at all.

**H2. No retry on place/close/modify at the client layer; close failures wait
for the next monitor cycle.**
`broker/mt5_client.py:286-349`: a single transient HTTP failure on
`close_position`/`modify_order` becomes `{"error": str(e)}`, and per C1/C2
most callers don't check it. An SL/TP-driven close that fails once is only
recovered if position sync later notices. (Contrast `trading/profit_sync.py:51`,
which does bounded escalating retry correctly.)

**H3. Cross-engine ownership is inverted: the breakout engine imports its core
market analysis from a sibling engine.**
`breakout_signal/signal_generator.py:22-33` imports ten indicator functions
(`compute_htf_bias`, `compute_adx`, `identify_key_levels`, `get_session`,
`is_news_window`, …) from `test_signal.signal_generator`;
`breakout_signal/breakout_signal_service.py:586` lazily imports
`test_signal.market_context`. Per the project's own rule
(`30-architecture.md`: used by 2+ services → `utils/`), these belong in
`backend/src/utils/`. As written, tuning the test/bounce engine's
`identify_key_levels` (`test_signal/signal_generator.py:309`) silently
re-prices live breakout signals. Separately, level detection exists three
times (`test_signal/signal_generator.py:309`,
`reversal_engine/level_detector.py:353`, `reversal_engine/ict_patterns.py:48`)
with no authoritative one.

**H4. Main trading DB connection is the weakest-configured connection in the
app.**
`db/database.py:170`: `sqlite3.connect(_DB_PATH, check_same_thread=False)` —
no `timeout=`, no `busy_timeout`, WAL only via the schema script
(`database.py:203`) rather than at connect. Meanwhile two threads (event loop
+ `db-worker`) both write through per-thread connections with no
application-level write lock — many call sites bypass `to_db_thread`
(`runtime.py:747,768-769,1068`; all of `services/positions/repo.py`, which is
"synchronous on purpose"). Under a disk stall this is the shape that yields
`database is locked` on a trade write. The per-engine adapter
(`db/sqlite_adapter.py:20,40-88`) does all of this correctly — `timeout=10`,
WAL at connect, an `RLock` around every op — the main DB just never got the
same treatment. Additionally ~10 modules re-open the main DB by reaching into
the private `database._DB_PATH` with raw `sqlite3.connect(...mode=ro)`
(`breakout_signal_repo.py:697`, `test_signal_repo.py:712`,
`reversal_engine_repo.py:755,791`, `analytics/read_repo.py:212`,
`analytics/ai_analysis_repo.py:33,279,404`, `analytics/edge_stats.py:50`,
`telegram/repo.py:220`) — read-only, but outside every cache-invalidation and
env-switch mechanism `database.init()` (`:132-163`) so carefully implements.

**H5. `db/database.py` re-exports ~100 names *upward* from 17 service repos.**
Lines 1061-1251 import from `services/risk`, `services/cluster`,
`services/channels`, `services/telegram`, `services/ai`,
`services/notifications`, `services/positions`, `services/broker` — the bottom
layer depending on nearly every service. The architecture doc acknowledges
this shim and its consequence: any `db_module.get_risk_settings()` call
reaches a service repo invisibly to the never-import-repos contract. It also
makes `import database` execute half the service tree, with the
order-sensitivity bug already hit once (`database.py:1115-1123`, the
`_ANALYTICS_LAZY` workaround). This is the single biggest structural debt left.

**H6. The self-healer's "monitor crash" detection can never fire, and loop
tasks have no supervision.**
`services/health/self_healer.py:55-58` greps the log for
"Exception in monitor loop" / "Error in position monitor" — strings **no code
in the repo ever logs** (verified by grep; the actual message is
"Monitor loop error: %s" at `positions/monitor_cycle.py:229`, which matches
none of the patterns). The monitor shell itself (`runtime.py:632-641`) has no
try/except and no `add_done_callback`; `monitor_cycle`'s internal catch makes
a crash unlikely, but if the task ever does die (e.g. an exception in
`_make_monitor_ctx` itself, or in the post-`try` tail at
`monitor_cycle.py:231-260` — whose own handlers cover most but not the
`ctx.state` mutations), it dies silently: no log line, no restart, no TP/SL
management on open trades. None of the 13 tasks started at
`runtime.py:285-297` has a done-callback, and `shutdown()`
(`runtime.py:314-329`) cancels but never awaits them. Log-regex self-healing
is inherently fragile; at minimum the patterns must match real log lines.

**H7. Cluster: `services/cluster/remote/server.py` (1,196 L) is a god module,
and risk↔cluster is a genuine import cycle.**
`remote/server.py` mixes token persistence (`:96-131`), admin-machine
management, licence issuance/revocation (`:416-519`), rate limiting
(`:565-581`), building and shipping update ZIPs (`:582-655`), UDP LAN beacons
(`:984`), TLS server lifecycle, and websocket message dispatch — at least five
responsibilities that should be sibling modules. Module-level mutable session
state (`_allowed_tokens`, `_pending`, `_connected`, `_auth_failures` at
`:49-89`) is mutated from many concurrent handlers and fire-and-forget tasks.
The cross-service matrix shows `risk → cluster` and `cluster → risk` at 8
imports each (bidirectional), plus `trading↔broker`, `positions↔trading`,
`telegram↔trading`, `dpm↔trading` back-edges — services are a partially
tangled graph, not a DAG. `services/cluster/remote/client.py:306` also reaches
up into the composition root (`from backend.src.app import get_engine`).

**H8. `mt5_native.py:105` reconnect thread races the MT5 IPC channel.**
`threading.Thread(target=mod._reconnect_loop, daemon=True)` runs outside the
`asyncio.Lock` (`mt5_native.py:53`) that serializes `_call()`; its safety
depends on `mt5_bridge.py` (a different process's module, different
interpreter) holding `_mt5_call_lock` across connect/disconnect — an invariant
enforced nowhere visible from this file. A regression there means a reconnect
can tear down the terminal connection mid-order.

### Medium

**M1. ~90% duplicate `database.py`/`*_repo.py` pairs within each engine, and
~85-95% clones across engines.** Beyond C3's dead files: seven copies of the
same `get_perf_by_*` GROUP-BY template (`breakout_signal/database.py:593,607,621,643`,
`reversal_engine/database.py:577,591,605`, `test_signal/database.py:679,694,709`
plus their repo twins), three drifting `get_ml_metrics` implementations
(`breakout_signal/ml_engine.py:561`, `reversal_engine/ml_engine.py:467` —
which admits being "ported… for UI parity" — `test_signal/ml_engine.py:498`),
identical `record_outcome` label math in all three
(`b:344`, `r:386`, `t:221`), and parallel `adaptive_params.py` /
`claude_reviewer.py` / `velocity.py` twins between breakout and test_signal.
One arithmetic fix (e.g. `net_pnl_dollars` vs `pnl_dollars`, visible between
`breakout_signal/database.py:597` and `reversal_engine/database.py:581`) must
be made in 6-9 places.

**M2. Duplicate/divergent constants.** Highlights (fuller table in the
concurrency/config pass): `_STARTING_BALANCE = 1000.0` defined six times;
`_TP_CACHE_TTL`/`_TP_WAIT_LOG_INTERVAL` duplicated verbatim between
`runtime.py:156,529` and `positions/tp_tracking.py:29-30` (runtime copies are
stale leftovers); `MT5_SYNC_MISS_THRESHOLD = 2` at `runtime.py:676` is dead
(comment admits the live value comes from expert tunables);
`_SIGNAL_MAX_AGE_S` synced by comment ("must match…") between
`reversal_engine_service.py:71` and `reversal_engine_correlate.py:33`; level
cooldown 1800 vs 2100 between reversal and breakout engines with no stated
reason; virtual lot sizes `0.1` hardcoded separately in
`reversal_engine_manage.py:23` and `breakout_signal_service.py:59`;
`_ML_BLOCK_THRESHOLD = 0.0` (`reversal_engine_live_execute.py:29`) gates live
placement and is not tunable; exit-ladder fractions hardcoded at
`reversal_engine_manage.py:52-54` and `breakout_signal_manage.py:27-28`. Config
itself lives in four unrelated stores (config.yaml via `config/__init__.py:70-187`,
`vantage_risk_settings`, `app_config` JSON blobs via
`expert_params.py`/`strategy_params.py` — the good pattern — and per-engine
`*_config` tables) with five different read APIs and cache stories.

**M3. Money-relevant failures logged at `debug`.** MT5 sync errors
(`monitor_cycle.py:237`), pending-activation errors (`:217`), residual-check
failure (`runtime.py:721`), circuit-breaker/watermark update failures
(`close_trade.py` record_close blocks). A broker desync should never be
invisible at default log level. 718 `except Exception` sites overall in
`backend/src` (161 immediately followed by `pass`), zero truly bare `except:` —
the discipline exists; the level and the unchecked-return pattern are the gap.

**M4. Engine repos reach across into main-DB/Telegram tables read-only**
(`reversal_engine_repo.py:748,785`, `test_signal_repo.py:740,751`) rather than
going through `signals/`, so `signals/` is not the sole owner of Telegram
signal data. `signals/` itself is otherwise the clean boundary: `parser.py`
is pure Telegram text parsing, distinct store and lifecycle from the engines.

**M5. `docs/system/rules/30-architecture.md` is stale on the per-engine `_conn()`
paragraph** — "per-engine research databases use their own `_conn()`, which
does not nest… known gap" now describes only the dead `database.py` files;
the live repos use the adapter's properly-nesting `transaction()`
(`breakout_signal_repo.py:270,331,432`, `reversal_engine_repo.py:352,389`).
The doc will send the next auditor to the wrong module. Remaining real
atomicity gaps: read-then-write with no transaction in `move_sl_to_be`/
`set_stop_loss` (`reversal_engine_repo.py:362-378`,
`breakout_signal_repo.py:307,317`).

**M6. Hardcoded deployment identity.** Admin server IP `217.155.25.160`
hardcoded in 6+ files (`config/licence/client.py:15`,
`cluster/remote/tls.py:24`, `cluster/remote/ip_check.py:16`,
`cluster/remote/server.py:4,1144`, …); a personal email address hardcoded as
the self-healer notification target (`services/health/self_healer.py:41`,
`_TO_EMAIL = "simon.moore@outlook.com"`). `bot_infra.py:41` uses
`os._exit(0)` for headless restart — no flush/cleanup of the DB worker.

**M7. `mt5_client.py:298-303`** returns the raw non-2xx body from
`place_order`; a body without an `"error"` key makes `open_trade.py:336` see
`mt5_error = None` and insert a trade row with `mt5_ticket=None` (phantom
trade). Also `mt5_client.py:37`: the tick-failure streak/recycle counter is a
module-level global shared across client instances.

### Low

**L1. `runtime.py` (1,310 L) and the facade are fine as designed** — ~39
public methods, mostly 1-3-line delegations, guarded by `facade_audit`; the
size is comments plus context builders. Splitting further is not the priority;
C1/C2/H6 are. The `_ema` helper at `runtime.py:159` and the duplicated
fast-poll comment (`runtime.py:635-640` = `monitor_cycle.py:262-267`) are
cosmetic.
**L2. `db/database.py` (1,251 L)**: ~500 lines are the schema DDL string plus
rationale comments; the actual logic is small. The re-export block (H5) is the
part that matters.
**L3. Shutdown does not await cancelled tasks** (`runtime.py:314-329`) — bridge
shutdown can begin while loops are mid-cancel.
**L4. Truly dead functions** beyond C3: `test_signal/ml_engine.py:489
_compute_mcc` (zero refs anywhere), write-only data paths `get_near_misses`
(`reversal_engine_repo.py:457`) and `get_latest_daily_research`
(`reversal_engine_repo.py:494`) — collected, never read in production.
**L5. `loop_monitor.py:84-85`** leaves `loop.set_debug(True)` on permanently —
useful, but it carries constant overhead on a live trading loop.

---

## Recommendations (prioritized)

1. **Check every `modify_order` result before any DB write or alert (C1).**
   Lift `safety_net.py:150-167`'s pattern (`try/except` + reject on
   `res.get("error") or res.get("success") is False`) into one shared helper in
   `services/broker/` and apply it at all ~14 sites. This is the direct
   descendant of a confirmed live loss. Falls under the frozen-close-path /
   stop-and-ask rules: needs owner sign-off and a demo session.
2. **Gate `record_close` on broker-close success in `monitor_loop.py:121-128`
   and abort ladder-close bookkeeping when a leg is rejected
   (`close_trade.py:294-312`) (C2).** Same sign-off caveat.
3. **Fix the news-calendar hot path (C4):** wrap the four call sites in
   `asyncio.to_thread` (or make the function async), and cache the `None`
   result at `news_calendar.py:49` so the 600 s TTL actually applies.
4. **Delete the dead code (C3):** the three engine `database.py` files
   (re-point the five characterization tests at the repos), plus
   `channels/rule_generator.py`, `breakout_signal/backtest.py` (or wire it —
   its docstring says it exists to gate recalibrations),
   `config/licence/client.py`, `test_signal/auth.py`. Then **fix
   `orphan_detector.py`** to scan `backend/src` at module granularity instead
   of the deleted `forex_trader/core/`, so this class of debt trips CI again.
5. **Unify the divergent tunables (C5):** `governor.py:209` must read
   `expert_params.get("max_unprotected_trades")`; `instant_entry.py:53-59,344,348`
   must read `strategy_params`. These are one-line-diff, user-visible-behavior
   fixes — but they change sizing/caps, so demo-session rules apply.
6. **Harden the offline-vs-empty ambiguity (H1):** make `get_positions`/
   `get_account` failures distinguishable (raise, or return a sentinel), or
   copy `position_sync.py:108-112`'s health-check guard to
   `runtime.py:713-722` and `position_sync.py:239-240`; log all of these at
   `warning`, not `debug` (M3). Add a small bounded retry for close/modify in
   `mt5_client.py` (H2).
7. **Give the main DB the adapter's connection settings (H4):** `timeout=10`
   and `PRAGMA journal_mode=WAL` + `busy_timeout` at `database.py:170`; expose
   a supported read-only accessor instead of ten modules importing
   `database._DB_PATH`.
8. **Make task supervision real (H6):** `add_done_callback` on all 13 runtime
   tasks that logs (at `error`) and restarts or alerts; fix the self-healer
   patterns to match log lines that actually exist; await cancelled tasks in
   `shutdown()` (L3).
9. **Move the ten shared indicators out of `test_signal` into `utils/` (H3)**
   and pick one authoritative level-detection implementation per concern.
10. **Plan the retirement of `db/database.py`'s upward re-export shim (H5)** —
    migrate `db_module.<name>` call sites to direct service-repo imports
    package by package, shrinking the shim to connection/schema only. Split
    `cluster/remote/server.py` by responsibility (token store, licence ops,
    updater, transport) (H7). Fix the stale `_conn()` paragraph in
    `30-architecture.md` (M5). Extract shared engine helpers
    (`get_perf_by_*`, `get_ml_metrics`, `record_outcome` label math) (M1) and
    collapse the duplicate constants (M2). Move the hardcoded admin IP and
    notification email into config (M6).
