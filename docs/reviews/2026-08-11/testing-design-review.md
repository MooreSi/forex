# Test Suite Design, Coverage & TDD-Alignment Review — 2026-08-11

Read-only review of test *design* (not just presence): TDD alignment, coverage
design, layout/fixtures, MT5 safety, exemplars vs anti-patterns. Companion to
the 2026-08-08 testing review, which was about the guardrail machinery. **The
suite was not run** (CLAUDE.md forbids concurrent full suites); evidence is from
greps, file reads, and one `--collect-only` on three directories.

Counts: **191 test files, ~32,500 LOC** across `tests/`.

---

## Summary

The guardrail machinery has been genuinely repaired since 2026-08-08. The two
High findings are both fixed: the vacuous orphan detector was replaced by
`orphan_modules.py`, a fail-closed whole-module dead-code gate wired into
`tools.checks` (`orphan_modules.py:172-181` raises `SystemExit` if a scan root or
entrypoint is missing); and the coverage ratchet is now fed by the suite —
`tools/checks.py:71-78` runs pytest with `--cov` and writes the JSON the gate
reads, with a stale-artifact guard (`checks.py:87-99`) and a new test
(`test_checks_feeds_coverage.py`) pinning that wiring. A new
`test_gates_fail_closed.py` closes the "fail-open on a missing directory" hole
(prior L1). MT5 safety remains excellent: **zero tests import `MetaTrader5`**,
and the process-spawn guard is asserted rather than assumed.

The negative-control doctrine — the single most important thing this repo's TDD
skill asks for — is **fully practiced in the structural gates**. Essentially
every gate in `tests/refactor/` plants an offender and asserts the detector
catches it (facade rogue-method, import-contract leak string, orphan planted in
a temp tree, structure-gate oversized file). This is the part of the suite most
faithful to the skill.

The problems are now about **test design, not guardrail plumbing**:

1. **13 gutted characterization files — 1,536 LOC that collect zero tests.** Each
   has a module docstring, a `fresh_db` fixture, a `_FakeBridge`, and helpers,
   but **no `def test_` at all**. The behaviour is covered (every one has a
   real `_surface` twin), but these are dead scaffolding that *reads* as
   coverage. This is precisely the "green is not evidence" failure mode in a new
   costume — a file named `test_handle_conservative_characterization.py`
   asserting nothing.
2. **Fixture sprawl is worse, not better.** `fresh_db` is now redefined locally
   in **115 files**; `_FakeBridge` in **69** (was ~40). The canonical conftest
   exists and is unused by the bulk of the suite.
3. **Layout still contradicts the protocol.** 124 files remain in the officially
   "legacy and closed" `tests/core/`; `tests/services/` is still 5 flat files
   with no per-service mirror; `tests/reversal_engine/` still has no
   `__init__.py` while sharing three basenames with two sibling dirs;
   `frontend/tests/` is still a one-`__init__.py` ghost inside `testpaths`.
4. **Money-critical floor protection still omits broker and runtime.** Both are
   in the tool's `CRITICAL` set but absent from the hand-set absolute floors, so
   a deliberate baseline-lowering of `services/broker` (58.3%) or `runtime.py`
   (72.2%) would pass the gate.

None of these can move money. But (1) and (2) are the kind of debt that makes
"the suite is green" mean less than it should, which is the exact thing this
codebase's rules exist to defend against.

---

## TDD alignment

### Scorecard

| Dimension | State | Evidence |
|---|---|---|
| Red-first / characterization→surface→relocation triad | **Strong** | Extraction packs consistently ship a `_characterization` + `_surface` pair; docstrings cite the migration task and describe real bugs found (e.g. import-time-timestamp staleness, `test_instant_entry_characterization.py:72-79`) |
| Negative controls on structural gates | **Strong / near-complete** | 10 of ~13 real gate tests plant an offender: `test_structure_gates.py`, `test_import_contracts.py`, `test_orphan_modules.py`, `test_facade_audit.py:51-62` (`_SYNTHETIC_EXTRA_PUBLIC`), `test_runtime_has_no_dead_imports.py`, `test_transaction_boundaries.py`, `test_gates_fail_closed.py:31-33`, `test_coverage_gate.py:89-96`. Metadata tests (pyproject, ci_workflow, installer) legitimately need none. |
| Tautologies / `assert True` / mock-return asserts | **Rare** | 0 `assert True`; no mass "assert on the mock's own return" pattern found |
| Assert-less *test functions* | **Rare** | The 13 assert-less *files* have **no test functions**, not assert-less functions — a different (worse) problem, below |
| Tests that pass if code is deleted | **13 files** | The gutted stubs import production modules at collection but assert nothing; and any file with 0 `def test_` cannot fail |
| Weak truthiness assertions (`is not None`, `len>0`) | **Modest** | ~57 occurrences across 191 files; acceptable but a slow drift away from rule #8 |
| Over-mocking | **Localised** | `test_email_scheduler_characterization.py` (39 patch / 14 assert), `test_bot_commands_infra_characterization.py` (9 patch / 4 assert / 2 tests) lean toward testing the wiring; most order-path files use hand-written fakes with call logs, per the skill |
| Import-time global mutation | **1 file** | `tests/test_engine.py:19-46` sets `os.environ`, `sys.path.insert`, and calls `db_module.init()` at module import — collection-order hazard, unsafe under xdist (prior L3, unresolved) |

### The 13 gutted characterization stubs (the headline TDD finding)

All in `tests/core/`, all 0 test functions, 1,536 LOC combined:

```
test_bot_commands_readonly_characterization.py   test_handle_protected_scale_characterization.py
test_dpm_handler_characterization.py             test_handle_scale_out_characterization.py
test_handle_be_runner_characterization.py        test_handle_scalp_runner_characterization.py
test_handle_conservative_characterization.py     test_handle_trail_stop_characterization.py
test_handle_conservative_trial_characterization.py  test_instant_entry_characterization.py
test_handle_no_sl_scale_characterization.py      test_pending_signal_activation_characterization.py
test_handle_orb_fixed_characterization.py
```

What happened: the code was extracted, a `_surface` twin was written and run
green, and per the protocol ("delete a characterization test only when an
identically-named surface twin exists") the *test functions* were deleted — but
the *file* (docstring, fixture, fake, helpers) was left behind. **Every one has a
populated surface twin** (e.g. `test_handle_conservative_surface.py`: 8 tests /
21 asserts; `test_instant_entry_surface.py`: 20 / 34; `test_dpm_handler_surface.py`:
16 / 39), so **no behaviour is lost**. But the residue is harmful:

- It reads as coverage that isn't there. Green from these files means nothing —
  the exact anti-pattern the skill opens with.
- It is 1,536 LOC of the fixture sprawl below (13 more `_FakeBridge` copies, 13
  more local `fresh_db`).
- The protocol says delete the *test* and "say so in the commit" — the intent
  is clearly to remove the file, not gut it in place.

**Fix: delete all 13 files** (the surface twins are the record). This is the
single highest-value cleanup in the suite.

### What is genuinely TDD-aligned

- Surface tests assert on **persisted state and call logs**, not return values:
  `test_handle_conservative_surface.py:115-139` asserts
  `bridge.partial_close_calls == []` / `== [...]` — rule #7 and #14 done right.
- Characterization files carry real red-first evidence: the comment at
  `test_instant_entry_characterization.py:72-79` documents a bug found *because*
  a module-level `now` went stale in a 6-minute run — a test that was watched to
  fail.
- The gate self-tests are the model the rest of the suite should imitate.

---

## Coverage design

The per-area ratchet is **well designed and correctly reasoned** — a single
global number would be gameable by adding cheap UI helpers while a trading
branch rots (`coverage_gate.py:1-27`), and the nested-subpackage split
(`area_of`, `:70-93`) correctly stops a relocated untested package from dragging
a parent's floor down. The Windows separator normalisation (`:57-68`) is the fix
for a real prior inert-gate incident. The two-job split in
`test_coverage_gate.py` — a live ratchet plus a **baseline-pinned absolute
floor** that holds without a coverage run — is a genuinely clever defence
against "temporarily" baselining `services/trading` down.

Design gaps:

- **Broker and runtime have no absolute floor.** `MONEY_CRITICAL_FLOORS`
  (`test_coverage_gate.py:35-41`) covers trading/risk/positions/signals/db only.
  Yet `coverage_gate.CRITICAL` (`:46-54`) *includes* `services/broker` and
  `runtime.py`, and `test_every_money_critical_area_is_marked_critical_in_the_tool`
  only checks one direction (floors ⊆ CRITICAL). Result: broker (58.3%) and
  runtime (72.2%) — both money-path — can be baselined downward and the gate
  stays green. Prior M2, still open.
- **The 2026-08-10 dead-code floor-lowering is defensible but is a lowering.**
  `breakout_signal` 32.0→20.3, `reversal_engine` 47.9→38.8, `test_signal`
  29.4→19.0 (`coverage_baseline.json:34`). The justification — deleting
  well-covered dead `database.py` clones removed covered lines without any live
  code losing coverage — is sound *if true*, and it is the one legitimate reason
  a shrink-only floor may drop. But it is exactly the move the rules forbid on
  sight, done to three areas at once, and there is no test asserting the deleted
  clones are actually gone (a negative control for the lowering itself). Worth a
  one-line structural test that those modules no longer exist.
- **Coverage measures execution, not verification — and the 13 stubs prove it.**
  Those files execute production import lines with zero assertions; their areas
  (`positions`, `trading`) still show high floors from the surface twins, so the
  number is honest here, but the stubs are a live example of why the floor is a
  hole-finder, not a victory condition (the tool's own docstring says so).

Under-covered money-adjacent areas remain: `services/broker` 58.3% (with
`mt5_native.py` — the native Windows broker path — still at ~0 direct test
references per the prior review), `runtime.py` 72.2%. `services/health` (22.8%)
and `services/backtest` (15.4%) have no dedicated tests but are not on the money
path.

---

## Test layout & fixtures

- **`tests/core/` — 124 files, still "legacy and closed."** It holds the bulk of
  the trading/positions/signals money-path tests. The protocol
  (`40-testing.md:61-64`) says move a file to its mirror dir when you touch it;
  the migration has not visibly progressed. This is not a correctness bug — the
  tests run — but it means the documented "tree mirrors `backend/src/`" is still
  aspirational, and `tests/services/` (5 flat files, no `trading/`, `risk/`,
  `broker/`… subdirs) is nearly empty.
- **`tests/reversal_engine/` has no `__init__.py`** while `breakout_signal/` and
  `test_signal/` do, and all three share three basenames
  (`test_engine_characterization.py`, `test_repo_transactions.py`,
  `test_service_surface.py`). `--collect-only` on the three dirs collects 105
  tests **without an import-mismatch error today** — because the two packaged
  dirs get dotted module names and `reversal_engine` is the lone unpackaged one,
  so nothing currently collides. But it is one edit away from the silent
  same-module overwrite the protocol warns about, and it plainly violates "every
  directory needs `__init__.py`." Cheap to fix. (Prior M3, unresolved.)
- **`frontend/tests/` is still a ghost:** only `__init__.py`, yet
  `pyproject.toml:55` keeps it in `testpaths` with a comment claiming a real
  suite. Pytest collects zero tests there. The real frontend tests are in
  `tests/frontend/` (5 files). (Prior M5, unresolved.)
- **Fixture sprawl has grown.** `fresh_db` defined locally in **115 files**,
  `_FakeBridge` in **69** (10 distinct fake families total: `_FakeEA` ×11,
  `_FakeTgReader` ×6, `_FakeEngine` ×4, etc.). Each local `fresh_db` reaches into
  `db._thread_local` / `db._db_executor` / `db._rs_cache` privates — 115 edit
  sites the day the DB layer moves. The canonical `tests/conftest.py` fixtures
  exist and are used by only a handful of files. (Prior M4, unresolved and
  larger.)
- **Determinism is well controlled:** only 2 real `time.sleep` calls
  (`test_ea_templates.py:80` a 10 ms mtime tick; `test_app_boots.py:80` a boot
  poll), no `assert True`, the market clock is pinned by the fixed-clock plugin.
  The one real network touch is a `socket` port-probe in the boot smoke
  (`test_app_boots.py:34`), which is the point of that test.

---

## MT5 test safety

**Strong and improved.** Confirmed:

- **Zero** tests import `MetaTrader5` (grep across `tests/`).
- The process-spawn guard is asserted, not assumed:
  `tests/core/test_bridge_process_relocation.py` asserts
  `bp.subprocess.Popen is subprocess.Popen` — a real broker/bridge subprocess
  cannot be spawned from that file.
- The bridge client test patches `httpx` rather than reaching a URL
  (`test_mt5_bridge_client.py`), and covers a real connection-reuse incident
  rather than a synthetic one.

On the fakes: there is **proliferation, not inconsistency.** 69 per-file
`_FakeBridge` classes is 69 places a canned response can drift from the real
bridge contract, and the 13 dead stubs contribute 13 of them. The shapes are
consistent (async `partial_close` / `modify_order` / `place_order` recording
call logs) and the safety story holds, but this is the same "40 copies" concern
the prior review raised, now larger. A single shared `FakeBridge` in
`tests/conftest.py` (parameterised by canned result) would remove the drift risk
and collapse the largest single fake family. Not urgent for safety; valuable for
faithfulness.

---

## Exemplars vs anti-patterns

### Good models to follow

1. **`tests/core/test_handle_conservative_surface.py`** — the template surface
   test. Realistic gold data (XAUUSD ~2400, 0.10 lots, 8-digit tickets), a
   hand-written fake with a call log, one Act per test, descriptive
   subject/scenario/expected names (`test_tp1_cleared_closes_80pct_and_moves_sl_to_be`),
   and assertions on the call log and persisted row rather than return values.
2. **`tests/refactor/test_facade_audit.py`** — negative-control done properly:
   `test_public_method_outside_allowlist_fails` (`:58-62`) plants a rogue public
   method (`_SYNTHETIC_EXTRA_PUBLIC`) and asserts the gate names it, alongside
   the real-tree green assertion. Every structural gate test should look like
   this, and most do.
3. **`tests/refactor/test_gates_fail_closed.py`** — encodes the repo's own
   founding incident as a test: monkeypatches the scan root to an empty tree and
   asserts the gate `raises SystemExit` rather than passing, with a real-tree
   negative control (`:31-33`).

### Anti-patterns to fix

1. **The 13 gutted characterization stubs** (listed above) — 1,536 LOC, zero
   tests, reads as coverage. **Delete them.** Worst offender by volume.
2. **`tests/test_engine.py`** — mutates `os.environ`, `sys.path`, and calls
   `db_module.init()` at *module import* (`:19-46`); 23 unittest-style tests
   ported wholesale from another repo; lives at the top of `tests/` outside any
   mirror dir. Collection-order hazard for the whole process, unsafe under
   `pytest-xdist`. Should be split into the mirror dirs and its import-time
   side effects moved into fixtures.
3. **`tests/core/test_email_scheduler_characterization.py`** — 39 patch sites to
   14 assertions across 9 tests; the assertions verify the mock wiring fired
   more than they verify a behaviour. Candidate for a lower-down fake (SMTP
   boundary) and payload assertions.
4. **`tests/core/test_bot_commands_infra_characterization.py`** — 9 patches, 4
   asserts, 2 tests; over-mocked relative to what it verifies.
5. **`frontend/tests/` in `testpaths`** — a vacuous suite entry: pytest is told
   to collect a directory that contains only `__init__.py`. Either move the
   frontend suite there or drop it from `testpaths` and fix the comment.

---

## Prioritized recommendations

1. **Delete the 13 gutted characterization stubs** (their surface twins are the
   record; note it in the commit as the protocol prescribes). Removes 1,536 LOC
   of fake-coverage, 13 `_FakeBridge` copies, and 13 local `fresh_db` copies in
   one move. Highest value, lowest risk.
2. **Add `services/broker` and `runtime.py` to `MONEY_CRITICAL_FLOORS`** at their
   current floors (58.0, 72.0) so a baseline-lowering of either money-path area
   trips the absolute-floor test, and make
   `test_every_money_critical_area_is_marked_critical_in_the_tool` assert set
   *equality* both ways.
3. **Add `tests/reversal_engine/__init__.py`.** One file; closes the last
   duplicate-basename hole and satisfies the protocol's own rule.
4. **Resolve the `frontend/tests/` ghost** — drop it from `pyproject.toml`
   `testpaths` (real frontend tests are in `tests/frontend/`) and fix the stale
   comment, or move the suite there.
5. **Add a structural test for the 2026-08-10 dead-code deletion** — assert the
   three deleted `database.py` clones no longer exist, so the floor-lowering has
   a permanent negative control proving it was a deletion, not a regression.
6. **Consolidate `_FakeBridge` into one shared conftest fake** (parameterised by
   canned result). Collapses the 69-copy / 10-family drift surface and is the
   natural companion to the `fresh_db` consolidation the conftest already
   prescribes.
7. **Begin the `tests/core/` → mirror migration for real**, starting with the
   money-path directories (`trading`, `positions`, `risk`, `signals`), one file
   per touched change as the protocol says — and move `tests/test_engine.py`'s
   import-time mutations into fixtures as part of it.
8. **Tighten the ~57 weak truthiness assertions** opportunistically toward
   specific values (rule #8) as those files are touched; low priority.

Net: the guardrails are trustworthy again; the *tests themselves* now carry the
debt — dead scaffolding, fixture sprawl, and an unfinished layout migration.
Recommendations 1–4 are cheap and make "green" mean more.
