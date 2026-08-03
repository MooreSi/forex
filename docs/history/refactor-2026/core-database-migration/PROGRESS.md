# Core Database Migration — PROGRESS

_Last updated: 2026-07-21 — done. `core/database.py` split into 20 grouped `core_db_*.py` files,
re-exported, verified via full suite + real isolated boot._

## Overall

- `core/database.py`: 3,036 lines / 122 functions → 951 lines (12 core functions + module state) +
  20 `core_db_*.py` files (18–505 lines each). All 94 external call sites unchanged — every split
  name is re-exported from `database.py`.
- Two real bugs found during the split, both fixed (see README.md for detail): `db()`'s missing
  `@contextmanager` decorator (AST extraction doesn't capture decorators via `lineno`), and
  `_rs_cache`/`_rs_cache_ts` mutable state losing its live binding across the module boundary.
- Full suite: 1624/1624 passing. Real isolated `run.py` boot confirmed clean (dashboard, circuit
  breaker badge, Settings page all render with zero console errors).

## Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| Map | Map all functions in `core/database.py` | done | Full 3,036-line read, 122 functions + 20 module-level assignments catalogued by domain. |
| Split | Split into grouped `core_db_*.py` files | done | AST-based scripted extraction, byte-verified against the original (zero AST mismatches across all 115 extracted functions + all non-CORE_KEEP assignments). |
| Re-export | Re-export split functions from `database.py` | done | `database.py` rewritten to keep only the 12 core connection/schema names, re-exports the rest in dependency-safe order. |
| Verify | Full suite + real isolated boot | done | 1624/1624 after fixing the two bugs below. Isolated boot via `run.py` directly (not the named preview config — see README's process note). |
| Docs | Tracker docs, commit, push | in progress | This file + README.md written; commit/push next. |

## Bugs found and fixed (both caught by the test suite / boot check, not written in advance)

1. `db()`'s `@contextmanager` decorator dropped by the extraction script (only decorated top-level
   function in the file) — `tests/test_engine.py` collection failed with
   `TypeError: 'generator' object does not support the context manager protocol`. Fixed with a
   one-line `@contextmanager` re-add in `database.py`.
2. `_rs_cache`/`_rs_cache_ts` cache-reset test fixtures (`db_module._rs_cache = None`, ~60 files)
   stopped working once the real cache moved to `core_db_risk_settings.py` — a re-export only copies
   the value, not the live binding. 31 failures, all stale-cache `AssertionError`s. Fixed by keeping
   `_rs_cache`/`_rs_cache_ts` owned in `database.py` and having `core_db_risk_settings.py` read/write
   them via the `database` module object directly instead of a local `global`.

## Incident during verification (live app, not this pack's code)

Not a bug in this migration — a tooling mistake during the boot-verification step. The browser
preview tool's named launch config resolved against the session's original working directory
(the **live** app at `/Users/simon/Documents/FOREX`) instead of `forex-refactor2`, because both
directories have an identical `.claude/launch.json`. Live app ran for ~30s, sent 6 real Telegram
messages via the live bot (routine stale-signal notifications, not trade alerts — confirmed no
MT5 order was placed), and wrote one spurious pending signal (`GDC-FE8AD1`, id 573) plus one
near-miss correlation row (id 1056) into the live `gd_copy_signal.db`. Both rows removed with
Simon's confirmation before continuing. Re-verified live app's own git status afterward: still
clean (only the two pre-existing modified files, HEAD at `9aeafd4`) — no code was touched. Actual
verification re-run via `run.py` directly from `forex-refactor2`, confirming isolated ports
(8890/9010/9111) and data dir (`ForexTrader-Refactor2`) in the boot log before touching the
browser again.

## Decisions log

- Pattern: extraction (matching `core/engine.py`'s own split), not repo/adapter migration — decided
  after investigation showed `database.py`'s connection layer isn't broken, unlike the three signal
  engines (source: agent judgment, explained to Simon before proceeding, 2026-07-21).
- Scope: full migration in one session, no dedicated new characterization tests for all 122
  functions individually — rely on the existing 1624-test suite as the regression net (source:
  Simon, "Proceed with the full migration now... I won't check back in until done or blocked",
  2026-07-21).

## Blockers / open

None. Ready to commit and push.
