# Data Layer Review — FOREX Trader (follow-up to 2026-08-08)

Date: 2026-08-11. Reviewer scope: SQLite schema & migrations (`backend/migrations/`),
broker+DB atomicity, transaction discipline, connection config, backups, retention,
reconciliation, and verification of every prior data finding. Read-only; nothing was
run, MT5 untouched.

## Summary and verdict

The two claims that mattered most are **true and well built**. The migration system is
not a rename of the old ALTER loop: it is a genuinely numbered, append-only registry
(`backend/migrations/registry.py`) applied fail-closed with a per-step
`schema_version` stamp, a money-critical schema pre-flight that refuses to boot on an
incomplete shape, and — the strongest part — a legacy-DB upgrade proof
(`tests/migrations/test_legacy_upgrade.py`) that builds three historical database
shapes from a base DDL that deliberately lacks the migrated columns and drives them to
head losslessly. Daily backups are real, wired into startup (`run.py:296`), tested, and
rotated (keep 30).

What has **not** moved is essentially everything that touches money at the moment of a
broker call: `record_close` is still not idempotent (its own callers document that),
the `max_open_trades` gate is still check-then-act across broker awaits, circuit-breaker/
risk-governor recording after a live close is still inside `except: log.debug`, and the
FK-ordered delete hazard in retention/reset is still in the code. This is deliberate,
not neglect: all of it sits in `docs/todo/refactor/stage3/` (plus stage1/phase2 030/040),
explicitly **blocked on Simon** (owner sign-off + demo session per the golden rules).
The review found the plans accurate about what landed and what didn't — the remediation
docs do not overclaim.

**Verdict: genuinely safer on the "don't lose the books" axis (migrations, backups,
busy_timeout, fail-loud backfills); essentially unchanged on the "don't corrupt the
books during a trade" axis, by explicit decision to gate money-path edits on the owner.**
Given a single localhost install and an existing (pre-dating the review) broker-poll
reconciliation loop that adopts orphans and closes vanished tickets, the residual risk
is bounded — but the close-path double-record hazard is real and live today.

---

## Previous findings — verification

| # | Prior finding | Status | Evidence |
|---|---|---|---|
| C2 | ~90 `ALTER … except: pass` on every boot, no schema_version | **FIXED** | `backend/migrations/registry.py:36-58` (`apply_migration` skips only duplicate-column/already-exists, `SystemExit` on anything else); numbered registry `registry.py:85-255`, per-step stamp `registry.py:275-290`; `verify_critical_schema` `registry.py:300-315` called from `database.py:245-246`; legacy shapes tested `tests/migrations/test_legacy_upgrade.py:59-117`; negative controls `tests/db/test_migrations.py:63-71`, `tests/migrations/test_migration_registry.py:83-96`. Backfills now fail loud too (`backend/migrations/backfills.py:26-39`) |
| C1 | Broker action + DB record not atomic, no reconciliation | **PARTIAL** | Open path unchanged: `open_trade.py:334` places the order, `:349` inserts the row — a crash between them still orphans a position *briefly*. But `backend/src/services/broker/position_sync.py` (pre-existing; the 08-08 review under-credited it) runs every 6 monitor cycles: closes DB-open/broker-gone trades from deal history (`:143-228`, miss-streak=2) and **imports untracked broker positions** (`:245-268`), so an orphan is adopted within ~30s — with a default strategy and no signal context, and only for python-managed trades. The full reconciliation service (startup scan, UNKNOWN resolution, report-only mode) is `stage3/030` — blocked on Simon |
| H2 | No backup story | **FIXED (core), PARTIAL (edges)** | `backend/src/db/backup.py` — SQLite online backup API, `maybe_daily_backup` (one/day, keep 30), wired at `run.py:293-300`, tested (`tests/db/test_db_hardening.py:33-73`). Gaps: backup runs **after** `db.init()`/migrations, so the promised backup-before-migrate hook (pack 050) never landed — on upgrade day the newest snapshot is post-migration; no restore procedure documented anywhere (grep "restore" over docs finds none); per-engine DBs (`re_signals` etc.) and same-disk-only destination out of scope (owner accepted, Q#4) |
| H1/H3-prior | FK-ordered delete hazard in prune + reset | **NOT FIXED** | Schema still declares child FKs with no ON DELETE action (`backend/migrations/schema_sql.py:103,128`); `retention_repo.prune_tables` still deletes `vantage_simulated_trades` without touching `vantage_partial_closes`/`vantage_ladder_legs` (`retention.py:72-79`), failure still downgraded to `log.warning` (`retention.py:81`); `reset_simulation_data` still deletes trades **before** partial closes and never deletes ladder legs (`trade_repo.py:335-345`). Pack 050's own progress notes (2026-08-10) admit this is the deferred half. Mitigant: retention defaults to 0/off (`retention.py:36-41`) |
| H5-prior (H3) | max_open_trades check-then-act race | **NOT FIXED** | `open_trade.py:203-206` reads `count_open_trades()` then awaits EA/bridge before the insert at `:349`. Same for the pause/breaker checks at `:181-198`. Slot-claim fix is stage1/phase2/030 — blocked on Simon |
| H6-prior (H4) | Breaker/governor recording swallowed at debug | **NOT FIXED** | `close_trade.py:262-263` (`[CB] outcome recording skipped` at `log.debug`), `:239-240` (RG), `:225-226` (DPM), `:214-215` (ledger push). stage3/050 ("un-swallow recording") — blocked on Simon |
| M1 | database.py god-file / re-export hub | **PARTIAL** | 1,252 → 457 lines; schema/migrations/backfills moved to `backend/migrations/` (commits 21fb117, 2d17b94). The ~190-line re-export hub and the `_ANALYTICS_LAZY __getattr__` hack remain (`database.py:266-456`), `_rs_cache` still lives here for tests (`:280-281`) |
| M4 | Inconsistent connection config; raw rw connects | **PARTIAL** | Main `db()` now sets `busy_timeout=5000` (`database.py:177`); WAL persistent via schema (`schema_sql.py:9`). Raw read-write `sqlite3.connect` outside both managed layers unchanged: `read_repo.py:212`, `ai_analysis_repo.py:33,279,404`, `telegram/repo.py:220`, `reversal_engine_repo.py:755,791`. `SqliteAdapter.exec()` executescript landmine unchanged (`sqlite_adapter.py`). The process-wide write lock from pack 050 was deferred |
| M5 | Every-boot data backfills outside a version gate | **PARTIAL (accepted)** | Backfills still run every boot **by documented design** (`backfills.py:1-17`: must catch legacy rows arriving via restore/old node), but are now named, ordered, and fail-loud instead of `except: pass`. The "editing mistake becomes recurring corruption" class remains, mitigated by the explicit list + tests (`tests/migrations/test_backfills.py`) |
| M2 | Retention deletes audit provenance | **NOT FIXED (dormant)** | `retention.py:72-79` unchanged; default off. Flagged to owner in handover docs |
| M3 | Cluster sync conflict/allowlist | **OUT OF SCOPE NOW** | Deployment reality is single install, localhost, no cluster — urgency dropped as instructed. Ledger upsert idempotency (`sync_repo.py`) still the right pattern |

---

## New / remaining findings

### High

**H1. `record_close` is not idempotent and the close UPDATE has no status guard —
double-close double-credits the balance.**
`trade_repo.apply_full_close` (`trade_repo.py:180-200`) runs
`UPDATE vantage_simulated_trades SET status='closed' … WHERE trade_id=?` with **no
`AND status='open'`**, then unconditionally `balance = balance + ?`. Any two of the
five close callers racing (monitor loop, position_sync, manual close, EA event,
ladder completion) records P&L twice and feeds the breaker twice.
This is not theoretical: `position_sync.py:66-75` documents a **confirmed live
duplicate** (ticket 1572181515, 2026-07-10) and the current defence is caller-side
exclusion (EA-managed trades skipped from the poll), not a guard where the money
moves. Failure scenario today: an EA heartbeat-timeout flips a trade back to
`managed_by='python'` (registry step 7 comment, `registry.py:167-171`) in the same
window the EA's own `trade_closed` event arrives → both paths record the close, sim
balance credited twice, breaker fed twice. The fix is fully specced
(stage1/phase2/040 — compare-and-set inside the existing transaction) and blocked on
Simon; it should be the first thing he signs.

**H2. Retention, if ever enabled, still cannot prune a seasoned database — silently.**
Same mechanics as the prior review (child FKs, `retention.py:72-81`,
`retention_repo.py:10-16`): the first closed trade with a partial-close row raises
`FOREIGN KEY constraint failed`, rolling back the entire prune inside the single
`db()` block, reported only as `log.warning`. The UI still offers the setting. Net
effect is fail-safe-by-accident (nothing is deleted), which is why this is High not
Critical — but the owner believes retention works, and the same ordering bug in
`reset_simulation_data` (`trade_repo.py:341-342`, trades before partial closes,
ladder legs never) makes **Reset Simulation** raise and roll back for any account
with partial closes: a user-visible feature that likely errors on every real install.

### Medium

**M1. Nested `db()` blocks can commit a failed inner operation's partial writes.**
`db()` (`database.py:185-196`) tracks nesting depth: only depth 1 commits/rolls back.
If an outer `db()`/`transaction()` block calls a repo function that opens its own
inner `db()` block, and the inner work raises but the **outer code catches the
exception and continues**, the inner op's partial writes are neither rolled back
(depth>1 skips rollback) nor isolated — the outer block's eventual commit persists
them. The `transaction()` alias (`db/__init__.py:3`) is the same object, so the
"declared transactions" gate verifies naming, not isolation. No live instance found
in the money path (close/insert paths let exceptions propagate), but the many
`except Exception: log.debug` wrappers in `record_close` sit exactly one refactor
away from this trap.

**M2. No pre-migration backup, and no restore runbook.**
`run.py:288` runs `init()` (migrations) before `run.py:296` takes the daily snapshot.
A migration that fails closed is safe; a migration that *succeeds wrongly* (bad
appended step that passes `verify_critical_schema`) is snapshotted over as the day's
backup. Yesterday's snapshot exists only if the app ran yesterday. Pack 050 listed
`test_backup_before_migrate_runs` — never implemented. And nowhere in docs/ (including
docs/simon-handover/) is there a "how to restore backup_YYYYMMDD.db" procedure; for a
non-technical operator the backup story is only half-delivered. Cheap fixes, no money
path, no Simon gate needed.

**M3. The sim ledger (`vantage_simulation_account`) still drifts and is now
officially distrusted rather than fixed.**
`close_trade.py:162-167` documents it: the balance is the app's own running P&L ledger
which "can and does drift from the real account", so peak-balance and risk-governor
comparisons now deliberately use the live MT5 balance instead. `apply_profit_sync`
(`trade_repo.py:271-297`) corrects the balance only on the *first* sync per trade and
only when the delta ≥ $0.01; H1's double-close, `add_to_sim_balance` callers, and any
missed profit sync accumulate permanently. Sensible triage — but the UI still displays
this number, and no periodic "reconcile ledger to broker balance" job exists or is
planned in any pack. Worth an explicit owner decision: either reconcile it on a timer
or label it an estimate in the UI.

**M4. Migration registry has no gate preventing edits to shipped steps.**
The registry's contract is append-only (`registry.py:10-14`) and
`test_registry_is_ordered_and_dense` catches renumbering, but nothing (checksum, gate,
frozen-file check) catches *editing the SQL inside an existing step* — on a stamped DB
the edited step silently never runs, recreating a quieter version of the old drift
problem. A per-step content hash recorded in `schema_version` (or a gate comparing the
registry against a committed manifest) closes the class. Low effort, high leverage for
a hand-maintained registry.

**M5. Untracked-position import adopts orphans with invented context.**
`position_sync.py:245-268` imports any unknown broker ticket with the *global default
strategy*, no signal linkage, and whatever SL/TP the position happens to carry. For
the crash-between-place-and-insert case this rescues management (good) but silently
converts a signal-driven trade into a default-strategy trade — different ladder,
different BE rules — with only a log line. stage3/030's "recovered, loudly flagged,
report-only first" design is the right correction; until then this behaviour deserves
a Telegram alert, not just `log.info`.

### Low

**L1. `_has_backup_today` keys on file mtime (`backup.py:60-65`)** — copying backups
back into the folder (e.g. during a manual restore drill) resets mtimes and can
suppress that day's real snapshot. Filename-stamp parsing would be exact.

**L2. Raw read-write analytics connections remain** (see verification table M4) —
they bypass busy_timeout and add untracked writer-capable handles. All should be
`mode=ro` URIs like `signal_lab_repo.py:59` / `edge_stats.py:50` already are.

**L3. `get_circuit_breaker_state()` at `open_trade.py:192` is a synchronous DB read
on the event loop** — inconsistent with the surrounding `to_db_thread` discipline;
harmless until a disk stall lands mid-open.

---

## What is genuinely healthy

- **The migration system.** Numbered, append-only, fail-closed with `SystemExit` and
  a clear operator message, per-step stamping so an interrupted upgrade resumes
  exactly, money-critical pre-flight (`CRITICAL_SCHEMA`) as a second line of defence,
  and — rare in any codebase — a real legacy-shape upgrade proof, with negative
  controls for every detector. The Alembic rejection rationale (`__init__.py:13-17`)
  is honest and correct for this deployment.
- **Backups exist, are tested, and use the right primitive** (online backup API,
  consistent under WAL, no downtime).
- **Transaction discipline inside the DB** remains good: multi-statement money writes
  (`insert_trade_and_activate_signal`, `apply_full_close`, `apply_profit_sync`,
  `reset_simulation_data`) are all under `transaction()` blocks; repo layering held
  (no SQL in frontend; the structure gate now counts `backend/migrations/` as data
  layer).
- **The two-writer-thread story is now documented truthfully** (`database.py:26-36,
  173-177`) and mitigated with `busy_timeout=5000`; per-thread cached connections with
  re-entrancy depth are a sound design for this scale.
- **The remediation planning itself.** Pack 050's progress notes accurately record
  what was deferred and why; stage3 cleanly quarantines every money-path change behind
  the owner gate with tests-first specs already written (010 dedup, 020 UNKNOWN state,
  030 reconciliation, 040 no-DB-close-on-failed-broker-close, 050 un-swallowed halts).
  The plans do not claim more than the code delivers — which made this verification
  unusually easy to trust.

## Priorities for the Simon session (data-layer view)

1. **phase2/040 record_close idempotency** — the one live double-count hazard (H1).
2. **phase2/030 slot-claim** and **stage3/050 un-swallowed halt recording** — cheap,
   specced, close the two remaining prior criticals' teeth.
3. Meanwhile, without Simon: FK-ordered deletes + loud prune failure (050's deferred
   half — not money-path), backup-before-migrate + a restore runbook (M2), registry
   step checksums (M4).
