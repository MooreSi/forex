# Core Database Migration

**Status:** done
**Domain:** refactor
**Created:** 2026-07-21

## 👋 Picking this up (agents start here)

Different shape from every other pack in `refactor/` (backend-foundation, breakout-signal-migration,
test-signal-migration, gd_copy_signal). Those all replaced ad-hoc `sqlite3.connect()` calls with the
shared `DbAdapter`/repo pattern because their connection layers had real atomicity/lastrowid bugs.
`core/database.py` does **not** have that problem — investigated first, before writing any code, and
confirmed it already has correct per-thread connections (`threading.local()`) and a working reentrant
`db()` context manager (via `_thread_local.depth`). This pack is a pure file-size split (3,036 lines,
122 functions, imported by 94 files), not a connection-layer migration. Same pattern `core/engine.py`
itself used earlier in `core-engine-wiring`: extract into grouped `core_db_*.py` files, re-export
every name from `database.py` so all 94 external call sites (`db_module.get_risk_settings()` etc.)
keep working completely unchanged.

## What we did & why

`core/database.py` had grown to 122 functions covering risk settings, circuit breaker, sync
infrastructure (node role/active-trader gating used by all 4 engines), channel strategy overrides,
telegram config/log, MT5 credentials, signal bus, AI-recovered-signal review queue, analytics, and
more — the largest remaining file in the codebase after `core-engine-wiring` finished. Split into 20
`core_db_*.py` files by domain, using an AST-based scripted extraction (not manual transcription,
given the blast radius): parsed the original file, extracted exact verbatim source per top-level
function/assignment, grouped by domain with explicit cross-file `needs` for the handful of
dependencies (e.g. `core_db_circuit_breaker` needs `get_risk_settings`/`update_risk_settings` from
`core_db_risk_settings`), then verified every extracted function's AST was byte-identical to the
original before touching `database.py` itself.

7 functions plus the module-level connection/schema state stayed in `database.py`
(`set_main_event_loop`, `to_db_thread`, `init`, `db`, `row_to_dict`, `_apply_schema`,
`_schedule_coro`, `_DB_PATH`, `_db_executor`, `_main_loop`, `_thread_local`, `_SCHEMA`) — the core
connection machinery every split file imports from. `database.py` re-exports all 115 extracted names
in dependency order so it remains a complete drop-in replacement for every existing caller.

## Two real bugs found while wiring, both fixed

1. **`db()`'s `@contextmanager` decorator was silently dropped by the extraction.** AST `lineno` for
   a decorated function points at the `def` line, not the decorator line, and the extraction script's
   "grab a leading comment block" heuristic only looks for `#`-prefixed lines, not decorators. `db()`
   was the *only* decorated top-level function in the file (confirmed by scanning every node's
   `decorator_list`), so this was a one-line fix once caught by `tests/test_engine.py`'s collection
   failing with `TypeError: 'generator' object does not support the context manager protocol`.
2. **`_rs_cache`/`_rs_cache_ts` mutable module state broke test fixtures after the split.** ~60 test
   files reset the risk-settings cache via `db_module._rs_cache = None` between tests. Once
   `get_risk_settings()`/`update_risk_settings()` moved to `core_db_risk_settings.py`, a plain
   `from core_db_risk_settings import _rs_cache` re-export only copied the *value* into `database.py`'s
   namespace — resetting `db_module._rs_cache` no longer touched the actual cache the functions read
   from, so stale risk settings leaked across tests (31 failures, all `AssertionError` on cached
   values from a previous test). Fixed by moving ownership of `_rs_cache`/`_rs_cache_ts` to
   `database.py` itself (the one true copy) and having `core_db_risk_settings.py`'s functions read/
   write them via `_database_module._rs_cache` instead of a local `global`. Checked for other
   externally-mutated module globals of this shape first (`grep` across `tests/` for `db.` /
   `db_module.` attribute assignment) — `_rs_cache`/`_rs_cache_ts` were the only ones.

## Verification

- Full suite: 1624/1624 passing after both fixes.
- Real isolated boot: `forex-refactor2`'s own `run.py` (isolated data dir `ForexTrader-Refactor2`,
  port 8890, MT5 bridge port 9010, EA bridge port 9111, remote-admin client disabled, no Telegram
  credentials configured) — dashboard rendered with zero console errors, "Circuit Breaker OK" badge
  rendered (exercises `get_circuit_breaker_state()` → `get_risk_settings()`, both from the new split
  files), Settings page rendered (exercises `core_db_credentials.py`). Deliberately did not touch any
  MT5 Bridge Control buttons (Start/Stop/Test Connection) — those talk to the same native Wine-hosted
  MT5 bridge process the live app can also use, so clicking them isn't a safe way to verify a database
  file split.

**Process note, not a code bug:** the first boot verification attempt used the browser preview tool's
named launch config, which resolved against this session's original working directory
(`/Users/simon/Documents/FOREX`, the live app) rather than `forex-refactor2` — both directories carry
an identical `.claude/launch.json`. That accidentally started the live app for ~30 seconds, sent 6 real
Telegram messages via the live bot, and wrote one spurious pending signal (`GDC-FE8AD1`) into the live
`gd_copy_signal.db`, since cleaned up. Re-ran the actual verification via `run.py` directly from
`forex-refactor2` with explicit isolated ports/data-dir confirmed in the boot log before touching the
browser again.

## Out of scope

Dedicated characterization tests for all 122 functions individually — not written from scratch.
The existing 1624-test suite already exercises `core.database` extensively (it's imported by 94
files across the app), and both real bugs the split introduced were caught by that suite, not a
purpose-built characterization pack. Non-function top-level assignments (`CANONICAL_CHANNELS`,
`_rs_cache`, etc.) were AST-verified for exact equivalence but not individually unit-tested beyond
that — same standard used for `core/engine.py`'s own extraction.
