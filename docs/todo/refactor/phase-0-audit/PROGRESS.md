# Phase 0 Audit — PROGRESS

_Last updated: 2026-07-25 — Checks 1-4 and the structure ratchets built, validated and run;
the `suggest_lot_size` defect fixed. The fixture collapse and the tracker corrections are
not started. All gates green._

## Overall

Built four AST-based checks for the defect class that let extractions be marked "Done"
without being wired in, plus four shrink-only structure ratchets. Each check was pointed at
a case with a known answer before being trusted, then run across all 78 `core_*.py`
modules. Nothing under `forex_trader/` was modified.

Headline: **10 orphaned functions, 456 LOC of dead code**, three of them undocumented.
Five of the seven on the order path share a single root cause -- a partial
`CloseTradeContext` -- which is also the dependency gating the trading phase.

Worst single finding, now fixed: **two reachable, disagreeing implementations of
`suggest_lot_size`**. Telegram auto-executed trades were sized without the Max Risk per
trade % ceiling that manual orders and bot commands applied -- the same UI field honoured
on two entry paths of three. Raised rather than fixed unilaterally, since it changes order
size on a live account; the owner chose to honour the setting everywhere. `engine.py`'s
copy is gone and the method delegates. Telegram-signal positions may now be smaller.

Note on the fix itself: it initially grew `engine.py` by two lines and the LOC ratchet
rejected it. Shrink-only applies to this work too, so the change was tightened until
`engine.py` came out three lines smaller (3,165 -> 3,162) rather than rebaselining upward.

## Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Orphan detector | done | AST + alias resolution. Finds 10 functions / 456 LOC. 16 tests including negative controls and the keyword-argument false positive a grep produces. |
| 2 | Inline-twin comparator | done | Classifies identical / diverged / no twin. 12 tests on the normaliser. Surfaced the shared `CloseTradeContext` root cause. |
| 3 | Divergence detector | done | Retro-audit over git history. 6 tests. Validated by independently recovering the documented `core_run_tp_ladder` truncation (`current_sl = new_sl` + the breakeven alert). |
| 4 | Delegation checker | done | Static rather than the ~50 generated runtime tests originally planned -- see below. Found 7 unwired duplicates, one of them a live defect. |
| 5 | Structure ratchets | done | LOC / SQL / transaction / ui_db, all shrink-only with a checked-in baseline. |
| 6 | Test fixture collapse | not started | Prerequisite for phases 6-8, not an optimisation. |
| 7 | Correct the false tracker rows | not started | `core-engine-wiring/README.md:65` and the deferral rows. |
| 8 | Resolve `suggest_lot_size` | done | Owner chose one implementation with the ceiling applied. `engine.py`'s copy deleted; method delegates. CI green. |
| 9 | Fix the reference-repo transaction gap | done | `test_signal_repo.insert_signal` now atomic. Two of the three original findings were the gate's own false positives (DDL); gate corrected, offenders fell 16 files/35 fns -> 5/9. |
| 10 | Make the suite runnable and deterministic | done | Clock plugin (120 failures), pytest-asyncio (26), settings-cache isolation (the flakiness). Session-start hook installs the environment. |
| 11 | Fix the shared settings cache | done | `database.init()` now invalidates `_rs_cache`. A live demo/live-switch bug as well as a test one. Regression test added. |
| 12 | Eliminate the suite flakiness | done | Three causes, not one: two time-keyed caches (now behind a `register_cache_invalidator` registry) and, mainly, seven test modules freezing a "fresh" timestamp at import time so it aged past the 4-minute staleness threshold before the tests ran. **1996 passed, 0 failed.** |

## What validation was actually done

Each check was pointed at a case with a known answer before being trusted:

- **Check 1** — negative controls assert that wired extractions (`core_open_trade::open_trade`,
  `core_close_trade::close_trade`, `core_monitor_loop::check_sl`,
  `core_risk_governor::rg_check_halt`) are *not* reported, and that a keyword argument named
  `close_full_after_tps` in nine handler modules is not mistaken for a call.
- **Check 2** — the three new orphans were each confirmed by hand before being written up:
  `engine.py:135` imports four names from `core_profit_sync` and `close_full_after_tps` is not
  among them; `engine.py:73` imports only `pnl` from `core_fees_sizing`; `engine.py:39` imports
  `check_sl` from `core_monitor_loop`, not from `core_tp_trigger_tracking`.
- **Check 3** — reproduced the `core_run_tp_ladder` truncation from history alone, naming both
  lost statements that `core-engine-wiring/PROGRESS.md:509-530` records.
- **Check 4** — negative controls assert that `_check_sl`, `open_trade`, `close_trade` and
  `open_trade_from_signal` are *not* flagged. `_check_sl` matters most: it is reached through
  `from ...core_monitor_loop import check_sl as _check_sl_impl`, so a checker matching on the
  local name would report it falsely.
- **Ratchets** — the shrink-only logic is tested directly: growth fails, a brand-new violation
  fails, shrinkage passes, and one test asserts the checked-in baseline still matches reality,
  since a drifted baseline silently disables every gate.

## Two corrections made during the work, not after

- **Check 4 first ranked severity by statement count**, with a comment claiming a clean gap
  between wired delegators and duplicates. There is no such gap: `suggest_lot_size` sat exactly
  on the cutoff and was classed as a harmless wrapper, so CI passed on the audit's most serious
  finding. Replaced with a structural test -- a wrapper is a body that only delegates, however
  short.
- **The `ui_db` gate first reported 5 files**, contradicting the known 13. It only matched
  `from ...database import x`, missing `from forex_trader.core import database as db_module`,
  which is the form the pages actually use. Corrected: 14 files, 24 imports.
- **The transaction gate counted DDL as a write**, so two of its three findings against the
  reference repos were false -- a `try`/`except`-guarded `ALTER TABLE ADD COLUMN` and a schema
  `init`. Only `insert_signal` was a genuine defect. Fixed both: the repo is now atomic, and
  the gate ignores DDL and migrate-on-write statements while still counting any statement it
  cannot read statically.

## Corrections to earlier assumptions, recorded

- **"There are exactly 50 commits, one per pack."** False. That was an artefact of a shallow
  clone. Real history is 142 commits. Check 3 returned zero findings against the shallow clone
  and only worked after `git fetch --unshallow` — the same "green means fine" failure this pack
  exists to catch, which is why the test suite now skips loudly on a shallow clone instead of
  passing vacuously.
- **"`core_handle_orb_fixed` lost a trailing `log.info` at extraction."** Not at the boundary
  Check 3 examines. At the add-commit (`5d57f7ee`) the extracted copy already contained that
  line; the gap was introduced by a later edit, before wiring. The test asserting otherwise was
  wrong and was corrected to pin the real behaviour and document the limitation.

## The baseline, resolved

The suite is now runnable and deterministic in this container, and the 159 failures are
fully accounted for. See TESTING.md.

| Cause | Failures | Fix |
|---|---|---|
| Session gates read the wall clock; this ran on a Saturday | 120 | `tools/testing/fixed_clock.py`, on by default |
| `pytest-asyncio` absent, so async tests failed rather than skipped | 26 | session-start hook |
| `get_risk_settings()` cached across databases for 10s | the flaky remainder | `database.init()` invalidates; autouse fixture in `tests/conftest.py` |

The third was not a test-only problem. `cmd_switch_env` re-points the database without
clearing the cache, so for ten seconds after a demo/live switch the app read the *other*
environment's risk settings — session gates and the Max Risk per trade % ceiling included.
`init()` already closed stale connections for the same reason (bug found 2026-07-21); the
cache a layer up was missed. Covered by `tests/core/test_database_init_env_switch.py`,
which fails without the fix.

## Blockers / open

- None. Q4 is resolved: the five orphans were deleted 2026-07-27, dead code in `core/`
  fell from 456 LOC to 8, and the delegation allowlist is empty.
- The suite is green and deterministic, so it can now serve as the regression oracle the
  later phases need.
- QUESTIONS.md Q2 (is a separate live deployment still running?) remains unanswered. It
  does not block Phase 2, which is read-only, but it should be settled before phases 6-8
  touch the broker and trading paths.
