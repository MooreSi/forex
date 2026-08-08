# Data Layer Review — FOREX Trader (live-money MT5 system)

Date: 2026-08-08. Scope: `backend/src/db/`, all `*_repo.py` under `backend/src/services/`,
`backend/src/services/cluster/sync/`, installer, retention, backups. Read-only review;
nothing was run and MT5 was not touched.

## Summary

The data layer is a single-file SQLite design with a thoughtful, battle-scarred
concurrency story (dedicated DB worker thread, per-thread cached connections, WAL,
namespaced adapters per engine) and a genuinely good repo discipline — essentially all
SQL lives in `*_repo.py` / `database.py`, parameterised, with no user-input injection
paths found. The transaction discipline *within* the DB is also good: multi-statement
money writes go through `transaction()` blocks that commit or roll back together.

The three big structural risks are:

1. **No migrations framework and no schema version.** Upgrades rely on a boot-time
   `try/except: pass` sweep of ~90 `ALTER TABLE` statements that cannot distinguish
   "column already exists" from "migration genuinely failed", on a live-money DB.
2. **Broker/DB dual-write with no reconciliation.** Order placement and DB insert are
   two non-atomic steps; a crash between them leaves a real MT5 position with no DB
   record (or a closed position the DB still thinks is open), and there is no startup
   scan that reconciles MT5 positions against `vantage_simulated_trades`.
3. **No backup story at all** for the live database, and a retention/reset path that
   appears to violate its own foreign keys (likely failing silently) and, when it works,
   deletes accounting-relevant history.

`database.py` (1,252 lines) is less a god object in behaviour than in *shape*: ~740
lines of schema+migrations plus a ~190-line re-export hub whose import-order fragility
has already produced one real bug (the `__getattr__` lazy-import workaround at
`database.py:1115-1130` documents it).

---

## Findings

Severity scale: **Critical** (can lose/corrupt live-money records now), **High** (real
risk on a plausible path), **Medium** (defect or design debt with bounded impact),
**Low** (hygiene).

### Critical

**C1. Broker action and DB record are not atomic, and there is no reconciliation.**
- Open path: `backend/src/services/trading/open_trade.py:334-354` — `bridge.place_order()`
  (real MT5 order) succeeds first, then `trade_repo.insert_trade_and_activate_signal()`
  writes the row. A crash, DB error, or process kill between the two leaves a **live MT5
  position with no DB record**: no monitor loop manages it, no SL-to-BE, no ladder, no
  close path. The EA-managed branch (`open_trade.py:300-310`) has the same gap.
- Close path: `backend/src/services/trading/close_trade.py:112-125` —
  `bridge.close_position()` first, then `record_close()`. A crash between them leaves the
  DB row `open` for a position that no longer exists; the monitor loop will keep acting
  on it (and `close_trade` on it later will try to close a dead ticket).
- A repo-wide grep for `orphan|reconcile` finds only per-engine *virtual balance*
  reconciliation (`reversal_engine_repo.py:245`, `breakout_signal_repo.py:177`) — there
  is **no MT5-positions-vs-DB reconciliation at startup or on a timer**. The profit-sync
  loop (`trade_repo.apply_profit_sync`, `fetch_unsynced_closed`) corrects P&L *numbers*
  for rows that exist; it cannot detect a missing or stale row.
- Mitigations that do exist: MT5 rejection raises before any row is written
  (`open_trade.py:339-341` — no phantom trades), and `reopen_residual_trade`
  (`trade_repo.py:638-647`) repairs one specific residual-volume case.

**C2. Ad-hoc schema management with blanket exception swallowing on a live DB.**
- `backend/src/db/database.py:712-943` (`_apply_schema`): `CREATE TABLE IF NOT EXISTS`
  script plus ~90 idempotent-by-hope `ALTER TABLE ... ADD COLUMN` statements each wrapped
  in `try/except Exception: pass`. This catches *every* failure — locked DB, disk full,
  I/O error, malformed statement — not just "duplicate column name". A genuinely failed
  migration is indistinguishable from an already-applied one; the app then boots and
  trades against a schema missing columns, failing later at arbitrary call sites
  ("no such column" mid-trade). Same pattern in `sync_repo.py:65-89`,
  `test_signal_repo.py:167`, `breakout_signal_repo.py:147`, `signal_bus_repo.py:55`.
- There is **no schema_version table, no ordering guarantee, no record of what ran**,
  and no way to write a data-transforming migration that must run exactly once (the
  2026-07-23 rebrand backfills at `database.py:952-1024` are re-run on every boot and
  rely on their WHERE clauses being self-neutralising forever).
- Upgrade story via installer: `installer/FOREX_Trader_Setup.iss` installs code to
  `{localappdata}\FOREX Trader` and data lives separately under
  `{userappdata}\ForexTrader\data` (`.iss:67`, `backend/src/config/__init__.py:45-46,185`),
  so an upgrade preserves the DB and `_apply_schema()` runs at next boot. That works
  forward-only; **downgrade after a failed upgrade is undefined** (old code, new columns
  is mostly safe in SQLite, but old code + partially-applied new data backfills is not),
  and nothing verifies the schema is complete before trading starts.

### High

**H1. Retention prune (and simulation reset) very likely violate their own foreign keys — silently.**
- `db()` enables `PRAGMA foreign_keys=ON` on every connection (`database.py:172`), and
  the schema declares `vantage_partial_closes.trade_id` and `vantage_ladder_legs.trade_id`
  → `vantage_simulated_trades(trade_id)` with **no ON DELETE action**
  (`database.py:289-323`), and `vantage_simulated_trades.signal_id` → `vantage_signals`.
- `prune_historical_data` (`backend/src/db/retention.py:48-84` →
  `retention_repo.py:10-16`) deletes closed `vantage_simulated_trades` rows but **never
  deletes their `vantage_partial_closes` / `vantage_ladder_legs` children**. The first
  pruned trade that has a partial close (routine for every scale-out strategy) should
  raise `FOREIGN KEY constraint failed`, rolling back the *entire* prune (all tables,
  single `db()` block) — and the failure is downgraded to `log.warning`
  (`retention.py:81`). Net effect: retention likely does nothing on any seasoned install,
  while reporting itself as merely "failed" in a log nobody reads. Similarly deleting
  old `vantage_signals` rows whose trade row is younger than the cutoff (still retained)
  would trip the trades→signals FK.
- `reset_simulation_data` (`trade_repo.py:335-345`) deletes `vantage_simulated_trades`
  *before* `vantage_partial_closes` — same FK ordering problem; the reset should fail
  whenever partial closes exist. Both need a failing test to confirm, then child-first
  deletes (or `ON DELETE CASCADE`).

**H2. No backup story for the live database.**
- Grep across the repo for backup/copy machinery finds only *log* rotation
  (`run.py:29-40`, service log handlers). There is no `sqlite3 .backup`/`VACUUM INTO`,
  no periodic snapshot, no pre-upgrade copy in the installer, and no pre-migration copy
  in `_apply_schema()`. The accounting record of a live-money account exists as exactly
  one file (plus its WAL) on one disk — on the VPS, a disk failure or a botched
  migration is unrecoverable. The cluster ledger (`consolidated_trades`) mirrors only a
  per-trade summary (pnl, outcome, ticket), not the books.

**H3. Check-then-act races across await points on the money path.**
- `open_trade.py:203-206`: the `max_open_trades` gate reads `count_open_trades()` and
  then awaits the broker (`place_order` / EA handoff) before inserting the row. Two
  concurrent `open_trade()` coroutines (e.g. two Telegram signals landing together) can
  both observe `count=0` and both place real orders, breaching `max_open_trades` — the
  gate's own comment says it exists to guard "whichever node's table is about to receive
  the INSERT", but the INSERT is seconds away behind network awaits. Same shape for the
  circuit-breaker/pause checks earlier in the function. (Signal *activation* by contrast
  is claimed atomically — `claim_signal_activation`, `trade_repo.py:350-357` — the right
  pattern.)
- Two writer connections exist for the main DB (event-loop thread + `to_db_thread`
  worker, `database.py:36,83-98`) despite the comment asserting a single-thread access
  pattern; `db()`-block atomicity is per-connection, so cross-thread read-modify-write
  sequences (e.g. `UPDATE ... balance = balance + ?` are fine, but any Python-side
  read-then-write is not) can interleave.

**H4. Circuit-breaker and risk-governor updates after a live close are best-effort and silently skippable.**
- `close_trade.py:242-263`: recording a live loss into the global circuit breaker is
  wrapped in `except Exception: log.debug(...)` — a failure here (DB locked, coroutine
  error) means consecutive live losses are *not counted* and the breaker never trips,
  with only a debug-level trace. Same for the risk governor (`:229-240`) and DPM
  (`:217-226`). For a safety mechanism on a live account, a swallowed failure should be
  at least `warning`/alert, ideally a trading pause.

### Medium

**M1. `database.py` god-file / re-export hub (1,252 lines).**
- Composition: connection kernel (~200 lines, genuinely core), 507-line `_SCHEMA`
  string, ~330 lines of migration/backfill statements, then ~190 lines re-exporting
  100+ names from 20 repo modules "so every existing `db_module.<name>` call site works
  unchanged" (`database.py:1061-1252`). The hub makes import order load-bearing — the
  `_ANALYTICS_LAZY` `__getattr__` hack (`:1115-1130`) exists because an eager import
  already broke boot once, and `_rs_cache` must live here instead of in its own repo
  (`:1069-1076`) because tests poke it through this module. Split out: (a)
  `schema.py` + a real migrations module, (b) retire the re-export hub by moving call
  sites to the repo modules (mechanical, gate-checkable), leaving `database.py` as the
  ~250-line connection/executor kernel.

**M2. Retention deletes audit provenance for live trades.**
- Even fixed, `prune_historical_data` (`retention.py:72-79`) deletes
  `telegram_messages`, `vantage_tg_signals`, `ai_recovered_signals` age-only. These are
  the provenance of why a live trade was opened (raw signal text, parse, AI extraction).
  A still-open or recently-closed live trade whose originating message is older than the
  window loses its audit trail. Closed trades themselves (with realised P&L that the
  `vantage_simulation_account` balance was built from) are deleted too — after pruning,
  the balance is no longer derivable from retained rows; only the unpruned
  `consolidated_trades` summary survives. Default is 0/indefinite (good), but the UI
  lets a user turn a live account's books into a 30-day window with no export step.
- Not covered by retention at all (unbounded growth, minor): `dpm_trade_performance`,
  `consolidated_trades`, `mt5_connection_events`, `vantage_claude_commentary`,
  `vantage_telegram_log`, and every per-engine DB (`re_signals`, `bo_signals`,
  `test_signals`).

**M3. Cluster sync: no conflict detection, allowlist drift is a proven failure mode.**
- Design: VPS server is authoritative for settings; Mac sends proposals, mirrors
  confirmed state (`sync/server.py:523-547`, `sync/client.py:401-421`). No timestamps or
  versions anywhere — convergence is "server wins", with the client's persisted
  `_pending_settings` queue (`client.py:59-133`) protecting only keys with an unsent
  local edit. If the VPS restarts with stale state while the Mac has no pending edit,
  the Mac silently adopts the stale value; two simultaneous edits on both nodes resolve
  to whichever proposal lands last, with no notice.
- The `_SYNCED_SETTINGS_KEYS` allowlist (`server.py:85-176`) is the right security call
  (credentials can't leak) but the file's own comments document **six separate incidents**
  where a new setting was forgotten and the whole proposal was rejected
  ("no recognised settings keys"), leaving nodes divergent for weeks (`server.py:99-149`).
  There is no gate/test forcing new `vantage_risk_settings` columns to be classified
  as synced/not-synced.
- Trade data sync is summary-only and **idempotent by design** — good:
  `record_consolidated_trade` upserts on `UNIQUE(node_id, trade_id)` with
  COALESCE-protected partial updates (`sync_repo.py:107-138`), so redelivery after
  reconnect can't duplicate or clobber. Ledger pull on reconnect (`client.py:293,385-390`)
  re-applies the full window through the same upsert. The operational trade tables are
  deliberately never merged (`sync_repo.py:29-35`) — divergence there is permanent by
  design and only papered over in History views via ticket-keyed fallbacks.

**M4. Concurrency configuration is inconsistent across the three connection layers.**
- Main DB `db()` connections: no explicit `timeout` (default 5s busy wait), WAL set via
  the schema script (persistent, fine) — `database.py:170-172,203`.
- Namespaced adapters: `timeout=10`, WAL, RLock-serialised single shared connection —
  `connection.py:49`, `sqlite_adapter.py:20,40`.
- Assorted raw `sqlite3.connect` in analytics: some correctly read-only
  (`file:...?mode=ro` — `signal_lab_repo.py:59`, `edge_stats.py:50`,
  `breakout_signal_repo.py:697`), but `read_repo.py:212`, `ai_analysis_repo.py:33,279,404`,
  `telegram/repo.py:220`, and `reversal_engine_repo.py:755,791` open plain read-write
  connections outside both managed layers. Under WAL these mostly work, but they bypass
  the busy-timeout/locking conventions and add writer-capable handles nobody tracks.
- `SqliteAdapter.exec()` uses `executescript`, which **implicitly commits any open
  transaction** before running — calling `exec()` inside a `transaction()` block would
  silently break its atomicity (`sqlite_adapter.py:66-70`). No current caller does; it's
  a landmine.

**M5. `_apply_schema` runs data-mutating backfills on every boot outside any version gate.**
- `database.py:952-1024` (order_type backfill, rebrand renames, `instant:` prefix
  strips, dpm backfill) execute on every startup and every demo/live switch. Each must
  remain individually self-neutralising forever; a future editing mistake turns one into
  a recurring data corruption. A one-shot migration record would eliminate the class.

### Low

**L1. SQL injection surface is effectively internal-only, but the dynamic-SQL idiom is fragile.**
- All user-facing values are parameterised. Interpolated *identifiers* come from fixed
  literal sets or internal dict keys: `update_risk_settings`/`update_fee_settings`
  set-clause from caller dict keys (`risk_settings_repo.py:61-63,141-143`),
  `update_trade_fields`/`update_signal_fields` (`trade_repo.py:159,392`),
  `upsert_daily_correlation(**kwargs)` (`reversal_engine_repo.py:594-601`),
  `create_signal(data.keys())` (`reversal_engine_repo.py:287-290`),
  `retention_repo.prune_tables` (table/clause from a literal tuple). The sync server
  filters inbound proposal keys against `_SYNCED_SETTINGS_KEYS` before they reach
  `update_risk_settings` (`server.py:523-525`) and `_handle_engine_control` maps to a
  fixed key dict (`server.py:373-379`), so no remote path reaches identifier
  interpolation today. Risk is future misuse, not current exploit. A tiny
  `assert k.isidentifier()`/allowlist helper for set-clause builders would close it.

**L2. Repo-layer leakage is minimal.** The frontend contains no SQL (one comment hit in
`frontend/pages/telegram.py:416`); layering (`frontend → controllers → services → db`)
appears enforced. Remaining SQL outside `*_repo.py` files sits in service-level
`repo.py`/`database.py` modules that are repos in all but suffix, plus the analytics raw
connections in M4.

**L3. `init()`'s cross-thread connection close** (`database.py:149-150`) submits
`_close_thread_local_conn` to the worker and waits 5s, but any *other* transient thread
that ever called `db()` keeps a stale-path connection forever. Currently only two
threads call `db()` per the comments; nothing enforces that.

**L4. `close_db()` during `init_db()` re-init** (`connection.py:48`) closes an adapter
another thread may be mid-query on (RLock is per-adapter; close acquires it, so an
in-flight query blocks the close — acceptable, but a query issued *after* close raises
`ProgrammingError` rather than being redirected).

---

## Recommendations (prioritized)

1. **Add MT5↔DB reconciliation (C1).** On boot and on a slow timer, compare
   `positions_get()` from the bridge against open `vantage_simulated_trades` (+ ladder
   legs): alert-and-adopt orphan broker positions (insert a managed row), and mark
   DB-open/broker-gone rows closed via deal history. This is the single highest-value
   guard for a crash-vs-live-position scenario and requires no change to the frozen
   close path itself.
2. **Introduce a minimal migrations framework (C2).** A `schema_migrations(version,
   applied_at)` table and an ordered list of one-shot migration functions; keep the
   idempotent CREATE/ALTER sweep as a legacy bootstrap but replace `except Exception:
   pass` with `except sqlite3.OperationalError as e: if "duplicate column" not in str(e):
   raise`. Refuse to start trading if schema verification (expected columns per table)
   fails.
3. **Fix the FK ordering in prune and reset (H1)** — delete children first (or add
   `ON DELETE CASCADE` for partial_closes/ladder_legs), and write the failing test first
   per house rules. Raise prune failures to warning+UI surface, not a swallowed dict.
4. **Add a backup routine (H2).** Nightly `VACUUM INTO`/`sqlite3.Connection.backup()` to
   a dated file with N-day rotation next to the DB (and one copy before `_apply_schema`
   runs on a version change). Cheap, zero-downtime under WAL, transforms C2/H1 from
   "unrecoverable" to "restore".
5. **Close the max-open-trades race (H3):** re-check the gate (and circuit breaker)
   *inside* `insert_trade_and_activate_signal`'s transaction, or take an asyncio lock
   across the gate→broker→insert sequence per account.
6. **Escalate swallowed safety failures (H4):** circuit-breaker/risk-governor record
   failures after a live close should log at warning, fire the existing Telegram alert,
   and ideally set the pause flag.
7. **Split `database.py` (M1)** per the existing `/split-file` skill: schema+migrations
   out first (biggest chunk, no call-site churn), then burn down the re-export hub
   module-by-module.
8. **Retention safety (M2):** before deleting closed trades, require (or auto-run) an
   export/archive step; exclude provenance rows referenced by retained trades; add the
   unbounded tables to the policy.
9. **Sync allowlist gate (M3):** a test that diffs `vantage_risk_settings` columns
   against `_SYNCED_SETTINGS_KEYS` + an explicit `_NEVER_SYNCED` set, so a new column
   fails CI until classified.

## Open questions

- Is there any operational (out-of-repo) backup of the VPS data directory (VPS provider
  snapshots, scheduled copy)? The code shows none, but ops practice may exist.
- Has `prune_historical_data` ever been observed to succeed on a database containing
  partial closes? (H1 predicts it cannot; a log check or test would confirm.)
- The EA-managed branch: if the EA acks `trade_opened` but the process dies before the
  DB insert, does the EA itself carry enough state to re-announce the trade on
  reconnect, or is the position orphaned exactly as in the Python-bridge case?
- `update_risk_settings` is called from UI save handlers with dict keys assembled where?
  (Assumed fixed literals; not every caller was traced.)
- Demo/live switch (`init()` repoint): are the per-engine namespaced adapters
  (`connection.py`) also re-pointed on an account-env switch, or do engine DBs stay
  shared across demo/live? (`reversal_engine`/`breakout`/`test_signal` use their own
  files; their `init_db` call sites were not fully traced.)
- `consolidated_trades` keeps only summaries — is that accepted as the sole surviving
  record if retention prunes the source rows, or should retention be blocked while it
  is the only copy?
