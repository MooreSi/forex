# Guardrail Machinery & Test-Suite-as-Safety-System Review — 2026-08-11

Read-only review of the gate/ratchet machinery, `tools/checks.py`, CI, baseline
history, and fail-closed behaviour. Companion to today's
`testing-design-review.md` (test design) and the 2026-08-08 `testing-review.md`
(the original machinery audit). **No suite was run** (concurrent-suite rule);
evidence is file reads, `git log -p` on every baseline, and — new for this
review — the **live GitHub Actions run logs** via `gh`.

Prime directive for this pass: find gates that LOOK alive but cannot fail.

---

## Summary & verdict

The local machinery is now genuinely strong. Every 2026-08-08 High finding is
fixed and — more importantly — fixed in the fail-closed style: the orphan gate
(`orphan_modules.py`) raises `SystemExit` on a missing root or entrypoint, the
coverage ratchet is fed by the suite and refuses stale or absent data, import
contracts error on a missing package, and the broker/runtime money-path floors
that were the last unguarded baseline-lowering hole were added **today**
(`test_coverage_gate.py:43-44`). Baseline history is clean: no ratchet was ever
lowered except one documented, annotated dead-code adjustment.

**But CI — the thing that turns all of this from a habit into a mechanism — is
red on every run it has ever had, and structurally cannot go green.** The
workflow installs only `requirements.txt`, which contains **no pytest, no
pytest-cov, no pytest-asyncio**. I pulled the actual run logs: three runs exist
(all today, 2026-08-11, first push of the branch), and each fails in ~2m20s
with `No module named pytest` — the five gates pass, then the **test suite and
coverage ratchet fail without executing a single test**. So the two components
that verify behaviour and coverage have *never once run in CI*. This is the
repo's signature failure mode in its newest costume: not a gate that prints
"all good" over nothing, but a CI badge that is *always red*, which within a
week means the same thing — nobody reads it.

**Verdict:** locally, `python -m tools.checks all` is trustworthy and
fail-closed at every link I traced. Remotely, enforcement is still voluntary:
until three lines of test dependencies are added to the workflow, a future
agent who breaks the close path and doesn't run checks locally is caught by
**nothing**.

---

## Verification of previous findings

| Prior finding | Status today | Evidence |
|---|---|---|
| H1 (08-08): orphan gate scans deleted dir, vacuous | **Fixed** | `tools/checks.py:53-57` now runs `orphan_modules`; `orphan_modules.py:172-181` raises `SystemExit` on missing root/entrypoint; `tests/refactor/test_orphan_modules.py:77-90` pins both fail-closed paths + real entrypoints exist. Old `orphan_detector.py` kept only as a helper library (documented, `orphan_modules.py:4-8`) |
| H2 (08-08): coverage ratchet not fed | **Fixed** | `checks.py:71-78` runs pytest with `--cov` writing to the path imported *from the gate itself* (`checks.py:23`); stale artifact cleared first (`checks.py:87-99,138-139`); gate fails closed on missing json (`coverage_gate.py:96-102`); wiring pinned by `test_checks_feeds_coverage.py:20-27` |
| H3 (08-08): pyproject broken backend / missing deps | **Fixed for runtime** | `pyproject.toml:3` (`setuptools.build_meta`), deps synced, pinned by `test_pyproject_metadata.py`. **Test deps still declared nowhere — see H1 below** |
| M1 (08-08): no CI | **Half-fixed** | `.github/workflows/checks.yml` exists (commit `3a2edef`), runs the exact local command, pinned by `test_ci_workflow.py`. But it cannot pass — H1 below |
| M2 (08-08) / design-review #4: broker & runtime lack absolute floors | **Fixed today** — design review is already outdated | `test_coverage_gate.py:35-45` now includes `services/broker: 58.3`, `runtime.py: 72.2`; `test_broker_and_runtime_have_absolute_floors` (`:74-85`) pins their presence; negative control at `:88-95`. Landed in `6c52279` after the design review was written |
| Design review #1: 13 gutted stub files | **Fixed today** | Files deleted; `test_no_empty_test_files.py:37-39` makes the class structurally impossible, with a negative control (`:42-48`). `tests/core` is down to 117 files |
| Design review #2: fixture sprawl 115/69 | **Ratcheted** | `test_fixture_dedup.py`: `fresh_db` locals 114→66, `_FakeBridge` 69→56, equality-pinned (`test_baselines_are_not_slack`) so the baseline cannot carry slack |
| Design review #3 / M3: `reversal_engine` no `__init__`, dup basenames | **Fixed** | `test_layout.py:33-34` (all test dirs are packages, with negative control), dup-basename rule at `:46+` |
| M5: `frontend/tests/` ghost in testpaths | **Fixed** | Directory deleted; `pyproject.toml:55` is `testpaths = ["tests"]` |
| L1 (08-08): gates fail open on missing dirs | **Mostly fixed** | `import_contracts.py:228-234` and `structure_gates.py:96-99,121-124` now raise; pinned by `test_gates_fail_closed.py`. Residuals: M1/M2 below |
| MT5 import safety | **Holds, now gated** | Zero real `MetaTrader5` imports in tests; the invariant is now itself a test (`test_fixture_dedup.py:68-75`), so a future violation fails the build |
| Skips/xfails | **Clean** | Zero `skip`/`xfail` markers; 9 conditional `pytest.skip` calls, each with a stated reason (port-busy boot smoke, shallow-clone history audit, no-coverage-data ratchet, Inno constants). The port-8888 skip (prior L2) persists unchanged (`test_app_boots.py:46`) |

---

## Gate-by-gate fail-closed trace (what if the target vanishes?)

| Check (`checks.py:36-84`) | Target missing/renamed → | Verdict |
|---|---|---|
| structure gates | Controller dir gone → `SystemExit` (`structure_gates.py:96-99,121-124`). But loc/sql/transaction/ui_db just walk whatever `production_files()` finds — see M2 | **Fail-closed for controllers; partially fail-open elsewhere** |
| import contracts | Any `source_packages` dir gone → `SystemExit` (`import_contracts.py:228-234`); contract missing from baseline → regression (`:307-308`) | **Fail-closed** |
| runtime facade | `runtime.py` file gone → `read_text` raises → exit≠0 (accidental fail-closed). **Class renamed → `census` returns `{}` → 0 methods ≤ ceiling → CLI passes vacuously** (`facade_audit.py:63-67`). Missing baseline file → ceiling check disabled (`:95-98`). Missing allowlist → all publics flagged (fail-closed) | **Fail-open on class rename at the CLI** — see M1 |
| orphan modules | Root or any of 5 entrypoints missing → `SystemExit` (`orphan_modules.py:172-181`); allowlisted module that stops being an orphan → FAIL (`:261-267`, stale-entry check) | **Fail-closed, both directions** |
| boot smoke | `python -c "import backend.src.app"` — module gone/renamed → ImportError → exit≠0 | **Fail-closed** |
| test suite | `pytest tests/` — dir missing → exit 4; zero collected → exit 5; pytest-cov absent → unknown-option error | **Fail-closed** |
| coverage ratchet | `.coverage.json` absent → `SystemExit` (`coverage_gate.py:96-102`); baselined area no longer measured → "no longer measured (deleted? renamed?)" failure (`:127-129`); `area_of` shape pinned (`test_coverage_gate.py:117-124`) | **Fail-closed** |

Can `tools.checks all` pass with a component silently not running? No: `run()`
(`checks.py:102-115`) treats any nonzero subprocess exit — including an
uncaught traceback — as FAIL, and every component above errors rather than
prints-clean when its input is missing. The one composition-level gap is
selective invocation (M3 below).

---

## New findings

### High

- **H1 — CI cannot ever go green: the suite and coverage ratchet have never
  executed on a runner.** `checks.yml:31-34` installs only `requirements.txt`;
  neither it nor `pyproject.toml` declares pytest, pytest-cov, pytest-asyncio,
  or coverage anywhere (prior L7, now load-bearing). Verified against reality,
  not just the YAML: `gh run list` shows exactly **3 runs, all 2026-08-11 (the
  branch's first push), all failing**; the log of run 31500673625 shows the
  five gates pass in ~11s, then `test suite FAIL (0.0s) — No module named
  pytest` and `coverage ratchet FAIL — no coverage data`. Consequences: (a)
  behaviour and coverage enforcement is still 100% local/voluntary, exactly the
   08-08 M1 state but now with a red badge; (b) a permanently-red check trains
  everyone to ignore CI, which is how the next real failure ships. Note the
  irony: `test_ci_workflow.py` pins that CI *invokes* `tools.checks all` but
  nothing pins that CI *can run it*. Fix is small: a `requirements-dev.txt`
  (pytest, pytest-cov, pytest-asyncio, coverage) installed in the workflow,
  plus one assertion in `test_ci_workflow.py` that the install step covers the
  test dependencies. Environment otherwise checks out on the evidence: Windows
  runner matches production, `MetaTrader5` pip-installs fine (boot smoke passed
  in 5.3s on the runner — so import-time deps, licence and DB needs of the
  composition root are satisfied), tests create their own sqlite DBs, 30-min
  timeout is ample for a ~5-min suite, and the concurrency group (`checks.yml:
  13-15`) correctly serialises runs per ref (the phantom-failure rule).

### Medium

- **M1 — Facade gate passes vacuously if `TradingRuntime` is renamed.**
  `facade_audit.py:63-67`: class not found → `census` returns `{}` → 0 methods
  under any ceiling → `--check` prints OK. The suite covers this
  (`test_facade_audit.py:75-78` asserts survivors like `close_trade` are in the
  real census), but that protection lives in the *suite* — which `checks
  gates` skips and which CI currently never runs (H1). Until H1 is fixed, a
  rename passes CI's facade gate. One `if cls is None: raise SystemExit`
  matches the house style of every other gate.
- **M2 — Structure gates' four ratchets (loc/sql/transaction/ui_db) are still
  fail-open on a moved tree.** They iterate `od.production_files()` (repo-wide
  rglob) and `check()` flags only violations found *now*
  (`structure_gates.py:286-299`); a baselined path that disappears is silently
  dropped, and if `backend/` were renamed wholesale, `sql`/`transaction`/`ui_db`
  would pass on an empty scan. Only the controller gates fail closed. Mitigated
  in practice by the boot smoke and import contracts erroring on the same
  rename — but this gate on its own would print clean, which is the pattern
  this repo's history punishes.
- **M3 — Selective runs grade stale coverage.** `_clear_stale_coverage()` runs
  only when SUITE *and* COVERAGE are both selected (`checks.py:138-139`);
  `python -m tools.checks coverage` alone happily grades whatever
  `.coverage.json` sits on disk (one exists in the tree right now). The gate
  has no staleness/mtime check of its own (`coverage_gate.py:96-113`). Small
  hole, but it is the exact "trust old data forever" path H2 warned about,
  reachable via a documented CLI choice.
- **M4 — `mt5_native.py` behaviour is still untested.** References now exist
  (`tests/services/broker/test_make_bridge_debug.py:22-40` covers the
  `_make_bridge` *selection seam*), but no test exercises `NativeMT5Bridge`'s
  own request/response behaviour — the module closest to the real broker on
  the production platform. The broker floor (58.3%) is now protected against
  lowering, which locks the gap in rather than closing it.

### Low

- **L1 — Facade "only shrinks" has historical exceptions.** `git log -p
  facade_baseline.json`: method_count rose three times (74→75→78→79, commits
  `4998779`, `38eb439`, `84f02db`) during B9 relocations. Each is explained in
  its commit, and the allowlist independently blocks new *public* surface, but
  nothing mechanical stops `--update-baseline` raising the ceiling; the claim
  in `facade_audit.py:9-10` is a convention, not a ratchet.
- **L2 — Stale comment in `checks.py:68-70`**: claims "testpaths in pyproject
  already includes frontend/tests" — it no longer does (`pyproject.toml:55`,
  correctly). Harmless (SUITE passes `tests/` explicitly) but the comment
  documents a world that was deliberately abolished.
- **L3 — Boot-smoke port skip persists** (`tests/frontend/test_app_boots.py:46`):
  a developer with the app running never runs the deep boot test; on CI (port
  free) it would run — once CI runs tests at all.

---

## Ratchet baseline history (git log -p, all four baselines)

- **coverage_baseline.json** — 3 commits. Created `601a431`; areas added on
  the cluster move (`b66da2a`, additions only); **one lowering ever**:
  `da117b6` (2026-08-10) dropped breakout_signal 32.0→20.3, reversal_engine
  47.9→38.8, test_signal 29.4→19.0, with an in-file
  `_dead_code_adjustment_2026_08_10` annotation explaining that deleting 3,384
  LOC of well-covered dead `database.py` clones shrank the numerator without
  any live code losing coverage. Defensible and unusually well documented;
  the design review's suggested negative control (assert the clones stay
  deleted) is still worth one line. **No money-path floor was ever lowered**:
  broker has been 58.3 and runtime 72.2 since creation, and both are now
  pinned absolutely.
- **import_contracts_baseline.json** — counts only ever fell (99→60→59→50;
  utils contract 12→10→3). Clean.
- **facade_baseline.json** — 142→118→99→79→76→74, then the three small
  documented rises (L1), then 79. Net direction honest.
- **structure_baseline.json** — churn matches the refactor commits; the two
  zero-tolerance sections (sql, ui_db) are empty, i.e. enforced at zero.

---

## What is genuinely healthy

- **Fail-closed is now the house style, and it is tested.** Missing scan root,
  missing entrypoint, missing package, missing coverage data, vanished
  coverage area, stale orphan-allowlist entry — every one errors, and
  `test_gates_fail_closed.py` / `test_orphan_modules.py:77-90` pin the two
  founding-incident paths with real-tree negative controls.
- **The coverage wiring cannot silently drift**: the suite writes to a path
  imported from the gate (`checks.py:23,75`), stale artifacts are cleared, and
  `test_checks_feeds_coverage.py` pins the argv itself.
- **All seven money-path areas now carry hand-set absolute floors** that hold
  on every plain test run with no coverage pass needed, with a negative
  control proving the comparison can fail (`test_coverage_gate.py:88-95`).
- **Baseline history is honest** — one lowering in the repo's life, annotated
  in the file itself.
- **The suite's own hygiene is now gated**: no empty test files, all test dirs
  packages, no duplicate unpackaged basenames, fixture-count ratchets pinned
  at equality (no slack), and MT5-import-safety as an executable invariant.
- **The orphan allowlist is a debt ledger, not a rubber stamp** — six entries,
  each with an owner decision recorded, and the gate fails when an entry goes
  stale in either direction.
- CI design (single command, same as local; Windows runner; concurrency
  cancel) is right — it is only the dependency install that is wrong.

## The honest opinion asked for

If a future agent breaks the close path **and runs `tools.checks all`
locally**, the machinery catches it with high probability (~95%): the surface
tests assert on call logs and persisted rows, and the trading/positions floors
(85%) would flag deleted tests. If the agent **relies on CI**, the probability
today is **near zero for behaviour bugs** — CI runs only the structural gates
and boot smoke, because pytest isn't installed. Deleting a whole module fares
better even in CI (~90%): the orphan gate, import errors in dependents, or the
boot smoke will trip. **The weakest link is unambiguous: H1.** Everything else
in this machinery is now built to fail loudly; the one component whose entire
job is making the others unskippable has never successfully run its two most
important checks.
