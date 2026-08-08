# Testing & Tooling Review — 2026-08-08

Read-only review of `tests/`, `frontend/tests/`, `tools/` and the gate/ratchet
machinery for the live-money MT5 trading app. No test suite or app was run.

## Summary

The testing culture here is unusually strong: red-first TDD is documented and
enforced, MT5 is consistently faked, a pytest plugin pins the market clock,
and the guardrail scripts carry incident history in their comments. But the
exact failure mode this repo's own CLAUDE.md warns about — "a guardrail script
that scanned a deleted directory and printed 'all good' for months" — is
**happening again right now, twice**:

1. The **orphan detector gate is vacuous.** It scans
   `forex_trader/core/core_*.py` (`tools/refactor_audit/orphan_detector.py:34`),
   a directory that no longer exists. It prints "No orphaned functions found"
   on every run and passes `--check` unconditionally. Its own comment admits
   the glob "returns nothing", yet it is still wired into
   `python -m tools.checks all` as one of the gates.

2. The **coverage ratchet is not fed.** `tools/checks.py` runs the suite as
   plain `pytest tests/ -q` (`tools/checks.py:65`) — no `--cov`, no
   `--cov-report=json` — while `coverage_gate.py` requires `.coverage.json`
   (`tools/refactor_audit/coverage_gate.py:37`), which **does not exist in the
   working tree today**. The gate's docstring ("tools/checks.py does this for
   you", `coverage_gate.py:24`) is false. As wired, `tools.checks all` either
   fails its coverage step every run (training people to ignore it) or, if a
   stale `.coverage.json` is ever left behind, silently validates old data —
   there is no staleness check.

Beyond that: there is **no CI whatsoever** (no `.github/`, no git hooks, no
pre-commit) — every guardrail depends on a human remembering to run one local
command. `pyproject.toml` has an invalid build backend and omits roughly twelve
runtime dependencies that `requirements.txt` declares. The documented
tests-mirror-src layout is aspirational: the bulk of the money-path tests live
in the officially "legacy and closed" `tests/core/`, and `frontend/tests/` is
an empty package that pytest is configured to collect.

The money-path *logic* itself (trading, risk, positions, signals, db) is well
covered (83–92% floors) and the MT5 fake discipline is genuinely good — no
test imports `MetaTrader5`, bridges are per-file fakes, and one file asserts
outright that it cannot spawn a process. The weakest money-adjacent area is
`services/broker` (58.3% floor, and `mt5_native.py` / `manual_limit_order.py`
have zero test references).

---

## Gates & ratchets audit

`python -m tools.checks all` (`tools/checks.py:34-74`) runs five "gates", the
test suite, and the coverage ratchet. Per gate:

### 1. Structure gates (`tools/refactor_audit/structure_gates.py`) — ALIVE

**What it checks.** Four shrink-only ratchets against
`structure_baseline.json`: files over 800 LOC (`loc_report`, :67); SQL string
constants outside `*repo*.py`/`database.py` (`sql_report`, :120, AST-based);
repo functions with 2+ row-modifying writes not wrapped in `transaction()`
(`transaction_report`, :196); frontend files importing the database or sqlite3
(`ui_db_report`, :216). Plus two zero-tolerance controller rules: no
controller over 200 lines and controllers must be flat `*_controller.py`
modules (:285-291).

**Do its targets exist?** Yes. It walks `od.production_files()` — a live
repo-wide rglob — and `backend/src/controllers` exists. I verified every path
recorded in `structure_baseline.json` (16 loc entries, 3 transaction entries)
exists on disk today; none are stale. `sql` and `ui_db` baselines are empty,
meaning those two are effectively enforced at zero — correct, and a *new*
violation would fail.

**Caveats.** `controller_loc_report`/`controller_shape_report` return silently
if `backend/src/controllers` disappeared (:86-88, :110-112) — a rename would
make both zero-enforced rules vacuous with no warning. Low risk, but it is the
same pattern that killed the last guardrail.

### 2. Import contracts (`tools/refactor_audit/import_contracts.py`) — ALIVE

**What it checks.** Seven named layering contracts (:56-149): controllers
never import repos or the database, services never import controllers,
frontend never imports the database (all enforced at zero), frontend reaches
the backend only through controllers (baseline 59 coupling edges),
no NiceGUI in the backend (baseline 2), utils/config import nothing above
themselves (baseline 3). Counted per (source unit, module) edge so file
splits don't move the number (:209-222).

**Do its targets exist?** Yes — `backend/src/controllers`,
`backend/src/services`, `backend/src/utils`, `backend/src/config`, and
`frontend` all exist. **But** `violations_for` does `if not base.exists():
continue` (:228-229): if a scanned package were renamed, its contracts would
pass vacuously and silently. The module even documents having previously been
blind for months to `from <pkg> import <repo>` (:163-167) — the fix is good,
but the missing-directory hole remains.

### 3. Runtime facade (`tools/refactor_audit/facade_audit.py`) — ALIVE

**What it checks.** `TradingRuntime` in `backend/src/runtime.py` may only
shrink: method count ≤ 79 (`facade_baseline.json`), and every public method
must appear in `facade_allowlist.json` (41 lines) (:78-92).

**Do its targets exist?** Yes — `backend/src/runtime.py` exists and defines
`TradingRuntime`. **Caveat:** if the class were renamed, `census` returns `{}`
(:66-67) → 0 methods → under baseline → pass; and `load_baseline`/
`load_allowlist` return empty when their JSON files are missing (:96-104),
which disables the check rather than failing it. There is a suite test
(`tests/refactor/test_facade_audit.py`) but the missing-class case passes
silently at the CLI.

### 4. Orphan detector (`tools/refactor_audit/orphan_detector.py`) — **VACUOUS**

**What it checks.** Extracted-but-never-called public functions in
`CORE_DIR = REPO_ROOT / "forex_trader" / "core"` (:34), globbing
`core_*.py` (:145).

**Does its target exist? NO.** `C:\dev\forex\app\forex_trader\` does not
exist. `find_orphans()` iterates an empty glob, returns `[]`, prints "No
orphaned functions found", and `--check` passes on every run. The comment at
:32-34 acknowledges this ("the glob over it returns nothing, which keeps every
core_*-scoped check vacuously green"), and `orphan_allowlist.json` has
`"allowed": []`. Yet `tools/checks.py:51-55` still runs it as the "orphan
detector" gate with the rationale "extracted code that nothing calls" — which
it can no longer detect anywhere. This is, verbatim, the historical
deleted-directory guardrail failure. `tests/refactor/test_orphan_detector.py`
unit-tests only the `UsageCollector` alias logic on synthetic source strings —
there is no negative control asserting the scanned directory exists or that
the end-to-end scan can still find a planted orphan.

Note the module is not dead weight — `structure_gates` and `facade_audit`
import its `REPO_ROOT`/`production_files()` — but the *gate* is inert. Either
repoint it at the current extraction target (e.g. `backend/src/services`) or
remove it from `GATES` so green means something.

### 5. Boot smoke (`tools/checks.py:56-60`) — ALIVE

`python -c "import backend.src.app"`. Target exists (`backend/src/app.py`).
Import-only; the deeper boot check lives in
`tests/frontend/test_app_boots.py`, which starts `run.py` as a subprocess —
see Findings for its port-8888 skip behaviour.

### Coverage ratchet (`tools/refactor_audit/coverage_gate.py`) — **BROKEN AS WIRED**

**What it checks.** Per-area shrink-only floors from
`coverage_baseline.json` (29 areas), 0.5pp slack (:40), money-critical areas
called out (:46-54). The per-area design and the Windows path-separator fix
(:57-67) are both well reasoned. A separate suite test
(`tests/refactor/test_coverage_gate.py:36-42`) pins hand-set absolute floors
on trading/risk/positions/signals/db against the *recorded baseline*, so
baseline-lowering is caught without a coverage run — good design.

**Does its input exist? NO.** It requires `.coverage.json` at the repo root
(:37, :96-101); only a binary `.coverage` from Aug 4 exists. Nothing in
`tools/checks.py` generates it — `SUITE` is plain `pytest tests/ -q`
(:63-68) — despite `coverage_gate.py:24` claiming "tools/checks.py does this
for you". Consequences: (a) `python -m tools.checks all` as shipped cannot
pass its coverage step, so either developers are running `checks gates` and
skipping the ratchet, or they have learned that the last line of `checks all`
fails "normally" — both defeat the tool's stated purpose of one command with
nothing skippable; (b) if a `.coverage.json` is ever generated manually and
left behind, every later `--check` validates that stale snapshot forever —
there is no mtime/staleness guard.

---

## Coverage gaps map

Floors from `tools/refactor_audit/coverage_baseline.json`; test presence from
mapping test dirs/files against `backend/src/services/*` and
`frontend/pages/*`.

### Test tree vs backend

`docs/system/rules/40-testing.md:55-58` says the tree mirrors `backend/src/` — it does
not, yet. The bulk of trading tests (124 files) live in `tests/core/`, which
the same doc declares "legacy and closed". `tests/services/` has five flat
files and **no per-service subdirectories at all**; `tests/services/trading/`
etc. do not exist.

| Service area | Floor % | Where its tests live | Assessment |
|---|---|---|---|
| services/trading | 88.0 | `tests/core/test_{open,close,partial_close,instant_*,manual_market_order,fees_sizing,scan_messages_auto_execute,...}` | Good — but see untested modules below |
| services/risk | 86.7 | `tests/core/test_risk_governor_*`, `test_expert_params*`, `test_strategy_params*`, `test_trading_schedule*` | Good |
| services/positions | 86.3 | `tests/core/test_handle_*`, `test_monitor_*`, `test_tp_*`, `test_max_tp_*` | Good |
| services/signals | 83.6 | `tests/core/test_scan_messages_*`, `test_signal_*`, `test_pending_signal_activation_*` | Good |
| backend/src/db | 92.2 | `tests/refactor/db/`, `tests/core/test_database_*`, conftest | Good |
| **services/broker** | **58.3** | `tests/core/test_mt5_bridge_client.py`, `test_bridge_*`, `test_ea_*`, `test_untracked_*` | **Weak for a money path** |
| runtime.py | 72.2 | `tests/core/test_runtime_*` | Fair |
| services/telegram | 50.2 | `tests/core/test_bot_commands_*`, `test_tg_signals_*` | Fair |
| services/cluster | 50.4 / remote 21.7 / sync 32.0 | `tests/controllers/test_remote_*`, `tests/services/` sync tests | Weak — 2,692 stmts of remote/sync largely untested |
| services/dpm | 46.3 | `tests/core/test_dpm_*` | Fair |
| services/reversal_engine | 47.9 | `tests/reversal_engine/` (10 files) | Fair |
| services/analytics | 51.6 | `tests/core/test_trade_reporting_*`, `test_orb_report_*` | Fair |
| services/breakout_signal | 32.0 | `tests/breakout_signal/` (4 files) | Weak |
| services/test_signal | 29.4 | `tests/test_signal/` (4 files) | Weak |
| services/ai | 26.3 | `tests/core/test_ai_signal_fallback_*` | Weak |
| services/health | 22.8 | none dedicated | **No direct tests** |
| services/notifications | 36.4 | `tests/core/test_email_scheduler_*`, `test_telegram_alerts_*` | Weak |
| services/channels | 34.3 | `tests/core/test_sync_channel_rename.py`, scorecard test | Weak |
| services/backtest | 15.4 | none dedicated | **No direct tests** |
| backend/src/config | 14.6 | none dedicated | **No direct tests** |
| backend/src/utils | 29.8 | indirect only | Weak |
| controllers | 25.8 | `tests/controllers/` (3 files, of ~15+ controllers) | Weak |
| app.py | 19.2 | boot smoke only | By design |

### Untested money-path modules (zero test-file references)

- `backend/src/services/trading/manual_limit_order.py` — **places a manual
  limit order; no test references it at all** (its market-order sibling has a
  characterization/surface pair).
- `backend/src/services/trading/engine_reads.py` — no test references.
- `backend/src/services/broker/mt5_native.py` — the native Windows MT5
  connection path; no test references. This is the module closest to the real
  broker on the platform the app actually trades from.
- `backend/src/services/broker/history_import.py` — one reference only.

### Frontend

- `frontend/tests/` contains **only `__init__.py`** — an empty suite, yet
  `pyproject.toml` `testpaths = ["tests", "frontend/tests"]` with a comment
  claiming "frontend/ has its own suite since Phase 1; both must run by
  default". Pytest collects zero tests there; the claim is vacuous. The real
  frontend tests are `tests/frontend/` (3 files: boot smoke, page imports,
  package name-resolution).
- `tests/frontend/test_pages_render.py:33-38` builds its module list with
  `PAGES_DIR.glob("*.py")` — **flat files only**, so the `frontend/pages/
  trading/` package (10 modules, the main trading UI) is excluded from the
  import-check parametrization. It is partially compensated by
  `test_page_packages_are_wired.py` (static AST name-resolution over package
  modules), but nothing actually *imports* `frontend.pages.trading` in that
  suite.
- Frontend floor is 4.2% overall — accepted by design (import + boot checks
  instead of render tests), which is a reasonable trade and is documented.

---

## Findings (by severity)

### High

- **H1 — Orphan-detector gate scans a deleted directory and always passes.**
  `tools/refactor_audit/orphan_detector.py:34` (`CORE_DIR =
  REPO_ROOT/"forex_trader"/"core"`; directory absent), :145 (empty glob),
  wired as a gate at `tools/checks.py:51-55`. Identical to the historical
  incident CLAUDE.md:110-117 exists to prevent. No test asserts the scan
  target exists (`tests/refactor/test_orphan_detector.py` covers only
  `UsageCollector` on synthetic strings).
- **H2 — Coverage ratchet is not connected to the suite run.**
  `tools/checks.py:63-68` runs pytest without `--cov`;
  `tools/refactor_audit/coverage_gate.py:37,96-101` demands `.coverage.json`,
  which does not exist; docstring :24 falsely claims checks.py generates it.
  Result: `tools.checks all` cannot pass as documented, and any manually
  generated `.coverage.json` would be trusted forever (no staleness check).
- **H3 — `pyproject.toml` cannot build and under-declares dependencies.**
  `build-backend = "setuptools.backends.legacy:build"`
  (`pyproject.toml:3`) is not a real backend (verified:
  `ModuleNotFoundError: No module named 'setuptools.backends'`; correct value
  is `setuptools.build_meta`). `[project] dependencies` lists 6 packages while
  `requirements.txt` lists ~19: scikit-learn, numpy, joblib, lightgbm,
  yfinance, MetaTrader5, keyring, websockets, cryptography, python-dateutil,
  psutil, matplotlib, cryptg are all missing from pyproject. A `pip install .`
  produces a broken deployment of a live-money app.

### Medium

- **M1 — No CI, no hooks.** No `.github/workflows`, no `.gitlab-ci.yml`, no
  `.pre-commit-config.yaml`, no active `.git/hooks`. Every gate depends on a
  developer voluntarily running `python -m tools.checks all` — and per H2 that
  command currently can't go fully green, which actively erodes the habit.
  `checks.py:12-13` says it "works as a pre-commit hook or a CI step
  unchanged"; nothing uses it as either.
- **M2 — `services/broker` is money-path with a 58.3% floor and untested
  modules.** `mt5_native.py` (0 test refs), `manual_limit_order.py` (0 refs —
  trading, not broker, but same class of gap), and broker is in the gate's
  `CRITICAL` set (`coverage_gate.py:46-54`) yet **omitted from the hand-set
  absolute floors** in `tests/refactor/test_coverage_gate.py:36-42`
  (`MONEY_CRITICAL_FLOORS` covers trading/risk/positions/signals/db only;
  broker and runtime.py are unprotected against a deliberate baseline
  lowering).
- **M3 — Test layout contradicts its own protocol.** `tests/core/` is
  declared "legacy and closed" (`docs/system/rules/40-testing.md:61-64`) yet holds 124
  of 180 test files including all close-path tests; `tests/services/` has no
  subpackage mirror; `tests/reversal_engine/` lacks an `__init__.py`
  (present in every other test dir — the doc itself warns duplicate basenames
  without `__init__.py` make pytest silently run only one file, and
  `test_database_characterization.py` / `test_repo_transactions.py` /
  `test_service_surface.py` / `test_engine_characterization.py` all repeat
  across `tests/breakout_signal/`, `tests/test_signal/`, and
  `tests/reversal_engine/`).
- **M4 — Fixture sprawl acknowledged but unresolved.** `fresh_db` is defined
  locally in 118 files (17 variants per `tests/conftest.py:3-9`), each
  poking `db._thread_local` / `db._db_executor` / `db._rs_cache` privates.
  `make_engine`/local equivalents build `TradingRuntime.__new__` partial
  objects (`tests/conftest.py:104-125`) — documented as fragile in
  `docs/system/rules/40-testing.md:83-91`. The canonical conftest exists; migration has
  not started.
- **M5 — Empty `frontend/tests/` suite in `testpaths`.**
  `pyproject.toml` testpaths comment claims a Phase-1 frontend suite that
  contains only `__init__.py`. Either the suite was moved to
  `tests/frontend/` and the config/comment is stale, or files were lost.
  Vacuous-suite risk: pytest happily collects zero tests from it.
- **M6 — `tests/frontend/test_pages_render.py:33-38` misses page packages.**
  `glob("*.py")` excludes `frontend/pages/trading/` (the main trading UI)
  from the import check; only a static name-resolution test covers it.

### Low

- **L1 — Gates fail open on missing directories.** `import_contracts.py:228`,
  `structure_gates.py:86,110`, `facade_audit.py:66,96-104` all treat a
  missing target (directory, class, baseline, allowlist) as "nothing to
  check" rather than an error. One rename away from another H1.
- **L2 — Boot smoke skips silently when port 8888 is busy.**
  `tests/frontend/test_app_boots.py:45-46` — a developer who runs the app
  while testing never runs the boot gate; also hardcoded real port, 120 s
  timeout, `time.sleep(1)` poll loop (:80), full `run.py` subprocess. The
  skip is deliberate and documented, but a persistent local server means the
  gate is persistently skipped with only a skip line as evidence.
- **L3 — `tests/test_engine.py` mutates global state at import time.**
  Sets `os.environ["VANTAGE_DB_PATH"]`, `sys.path.insert`, and calls
  `db_module.init(_TEST_DB)` at module import (:19, :38, :46) — a
  collection-order hazard for the whole process, and exactly the "module
  import time" anti-pattern `docs/system/rules/40-testing.md:115-117` bans for
  timestamps. `pytest-xdist` is installed; this file is unsafe under it.
- **L4 — Fixed-clock plugin pins only two readers by rebinding module
  attributes.** `tools/testing/fixed_clock.py:64-65` replaces
  `dpm_engine.detect_session` / `is_weekly_market_closed`; any module that
  did `from ...dpm.engine import detect_session` before `pytest_configure`
  keeps the real-clock function. Works today; brittle to a refactor.
- **L5 — Dead tooling ships alongside live gates.**
  `divergence_detector.py`, `twin_compare.py`, `check_syntax.py`,
  `ast_normalise.py` and `delegation_allowlist.json` (its checker was deleted
  in M4 B10 per `facade_audit.py:28-32`) remain in `tools/refactor_audit/`.
  History tools are fine to keep, but they blur which scripts are
  load-bearing — the exact confusion that let H1 persist.
- **L6 — 12 tests assert nothing** (verified by AST scan; all are
  "no-op/does-not-raise" tests, e.g.
  `tests/core/test_strategy_params_sync.py:55,112`,
  `tests/core/test_mt5_position_sync_characterization.py:116`,
  `tests/frontend/test_pages_render.py:41` — the last is legitimately an
  import-succeeds test). Mostly acceptable, but the no-op tests could assert
  the absence of side effects instead of relying on "didn't raise".
- **L7 — Dependency hygiene.** Everything in `requirements.txt` is `>=` with
  no lockfile and no upper bounds; `keyring` fully unpinned; test
  dependencies (pytest, pytest-asyncio, pytest-cov, coverage) are declared
  nowhere (no dev extra, no requirements-dev.txt) yet the whole verification
  story depends on them; `cryptg` has zero direct imports (it is a telethon
  accelerator — fine, but worth a comment). `requires-python = ">=3.11"` with
  no upper bound; `tools/checks.py` and gate code use 3.10+ syntax
  consistently, so version support is coherent.
- **L8 — MT5 fake duplication.** ~40 per-file `_FakeBridge` classes across
  `tests/core/` rather than one shared fake. They are *consistent* in shape
  and the safety story is good — no test imports `MetaTrader5`, no test
  constructs a real bridge with a live URL and calls out
  (`test_mt5_bridge_client.py` patches `_request`;
  `test_bridge_process_relocation.py:105` asserts `Popen` is untouched) — but
  40 copies is 40 places for a canned response to drift from the real bridge
  contract.

### Positive observations (for balance)

- The negative-control doctrine (`docs/system/rules/40-testing.md:21-34`) is actually
  practiced in the gate self-tests (`tests/refactor/test_import_contracts.py`,
  `test_structure_gates.py`, `test_orphan_detector.py` — ironically the
  detector's *logic* is well tested even though its *target* is gone).
- `tests/refactor/test_coverage_gate.py`'s baseline-pinned absolute floors are
  a genuinely clever defense against ratchet-lowering.
- The autouse risk-settings-cache reset (`tests/conftest.py:55-80`) documents
  and fixes a real timing-dependence incident.
- The suite is essentially free of sleeps (2 real `time.sleep` calls, both in
  the boot smoke / a 10 ms mtime tick), has zero `skip`/`xfail` markers, and
  no module-level `now = datetime.now()` timestamps.

---

## Recommendations (prioritized)

1. **Fix or retire the orphan gate (H1).** Repoint `CORE_DIR` at the current
   extraction surface (e.g. scan `backend/src/services/**` for public
   functions with no production caller) or delete it from `tools/checks.py`
   `GATES`. Whichever you choose, add the missing negative control: a test
   that plants an orphan in a temp tree and asserts the scan finds it, and a
   test that fails when the scanned directory does not exist.
2. **Wire the coverage ratchet (H2).** Change `SUITE.argv` in
   `tools/checks.py` to include `--cov=backend --cov=frontend
   --cov-report=json:.coverage.json` (with `--cov-report=` quiet term), and
   make `coverage_gate.measure()` refuse `.coverage.json` older than the run
   (or delete it up front in `checks.py`). Until then, `checks all` cannot
   honestly go green.
3. **Fail closed on missing targets (H1/L1).** In every gate, turn
   `if not base.exists(): continue` into a hard error listing the missing
   path. This single pattern caused the historical incident and H1.
4. **Fix `pyproject.toml` (H3).** `build-backend = "setuptools.build_meta"`;
   sync `[project] dependencies` with `requirements.txt`; add a
   `[project.optional-dependencies] dev` extra with pytest, pytest-asyncio,
   pytest-cov pinned. Consider a lockfile (pip-tools/uv) for a live-money
   deployment.
5. **Stand up minimal CI (M1).** Even a single GitHub Actions job running
   `python -m tools.checks all` on push turns eight social conventions into
   one mechanical one. `checks.py` was explicitly written for this.
6. **Protect broker/runtime in the absolute floors (M2)** — add
   `backend/src/services/broker` and `backend/src/runtime.py` to
   `MONEY_CRITICAL_FLOORS` at their current floors — and write first tests for
   `manual_limit_order.py` (money path, zero tests) and `mt5_native.py`.
7. **Add `tests/reversal_engine/__init__.py` (M3)** — cheap, and the doc's own
   duplicate-basename warning applies today.
8. **Resolve the `frontend/tests/` ghost (M5)** — either move the frontend
   suite there as the pyproject comment claims, or drop it from `testpaths`
   and fix the comment.
9. **Include page packages in the import check (M6)** — extend
   `_page_modules()` to yield `frontend.pages.<pkg>` for package directories.
10. **Begin the fresh_db consolidation (M4)** file-by-file as conftest already
    prescribes; 118 local copies is the largest single source of future
    refactor breakage in the suite.
