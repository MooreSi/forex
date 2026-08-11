# Review remediation — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision). This is how
every agent sees where the work is. Keep it honest: a task reported Done that isn't is the exact
failure mode this repo's rules exist to prevent.

_Last updated: 2026-08-11 — rows back-annotated: several phase-3/4 items landed via stage2
(see Notes); remaining open work is the deferred 2/050 remainder, 3/020, 4/030, and the
Simon-gated money tasks (stage 3)._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

A money-touching task is **not** `done` on a green suite alone — it needs owner sign-off and a demo
session, both recorded in Notes.

## Overall
- Phase 1 (stop the bleeding): 050 (localhost bind) done; the money-path tasks moved to [stage 3](../stage3/README.md) (Simon-gated) on 2026-08-11
- Phase 2 (safety net): non-money core COMPLETE — 010/020/060/070 done; 050 backups+busy_timeout done (write-lock + FK-deletes deferred within 050, lower risk). 030/040 money-gated on brother.
- **"Trustworthy to run locally" bar essentially met:** guardrails real, localhost-only, no event-loop stalls, migrations fail closed, DB backed up daily, no lock-storms. Remaining toward the full goal: phase 3 structural cleanup + the money-path (brother).
- Phase 3 (expansion tax): not started — dead-code deletion gated on phase2/010
- Phase 4 (hygiene): not started
- **Gates:** `/safe-change` run on money tasks? no · `python -m tools.checks all` green? no (known: coverage step cannot pass — see phase2/010)
- **Demo session** (money tasks only): not done

## Tasks

| Phase | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 1 | order-send dedup / timeout / reconciliation / no-db-close / halts | YES | **moved to [stage 3](../stage3/README.md)** (2026-08-11) | — | Simon-gated; extracted so stage2 is workable today |
| 1 | [050 bind-localhost](phase1-stop-the-bleeding/050-bind-dashboard-localhost.md) | no | done (2026-08-10) | Claude/Darren | dashboard binds 127.0.0.1 by default; `host` config key + non-loopback warning; 7 new tests green |
| 2 | [010 gates-fail-closed](phase2-safety-net/010-guardrail-gates-fail-closed.md) | no | done (2026-08-10) | Claude/Darren | coverage fed; pyproject fixed; NEW module-reachability orphan gate (fails closed) replaces vacuous one; structure+import gates hardened to fail closed. 25 new tests. Green means green now. |
| 2 | [020 schema-migrations](phase2-safety-net/020-schema-migrations.md) | no | done (2026-08-10) | Claude | migrations fail closed (skip duplicate-column, abort on real error), schema_version stamp + pre-flight verify. Extracted db/migrations.py + db/schema_sql.py → database.py 1251→749 (bonus phase3/040 progress). Structure gate taught db/ = data layer. Full suite green. |
| 2 | [030 risk-gate-atomicity](phase2-safety-net/030-risk-gate-atomicity.md) | YES | not started | — | |
| 2 | [040 record-close-idempotency](phase2-safety-net/040-record-close-idempotency.md) | YES | not started | — | |
| 2 | [050 db-config-fk-backups](phase2-safety-net/050-db-connection-fk-backups.md) | no | partial (backups + busy_timeout done) | Claude | db/backup.py (daily snapshot, keep 30) wired at startup + `busy_timeout=5000`. 5 tests. Remaining: write-lock + FK-safe deletes (deferred, lower risk — see task notes). |
| 2 | [060 news-calendar-offload](phase2-safety-net/060-news-calendar-offload.md) | no | done (2026-08-10) | Claude/Darren | getter now a pure cache read (no ~10s inline urllib); background refresher started at boot; None result cached (fixed every-cycle refetch); fetch+decision logic byte-identical. 6 new tests. Q004 policy (trade-through) unchanged. Full suite green. |
| 2 | [070 update-channel-disable](phase2-safety-net/070-update-channel-disable.md) | no | done (2026-08-10) | Claude/Darren | already off by default; added `_remote_client_enabled` regression guard + loud unauthenticated-warning on opt-in + honest update-panel banner. 5 new tests. Gates+boot green. |
| 3 | [010 delete-dead-code](phase3-expansion-tax/010-delete-dead-code.md) | no | partial (3 clones deleted; 4 unwired await Simon) | Claude/Darren | Deleted the 3 superseded-dead database.py clones + 6 files/3384 LOC (fixed 3 entangled tests — their "still needed" comments were STALE, verified empirically). 4 built-but-UNWIRED modules remain, ledgered, awaiting Simon's wire-vs-remove call (Q002). |
| 3 | [020 engine-shared-code](phase3-expansion-tax/020-consolidate-engine-shared-code.md) | no | not started | — | |
| 3 | [030 frontend-restructure](phase3-expansion-tax/030-execute-frontend-restructure-pack.md) | no* | not started | — | delegates to existing pack |
| 3 | [040 split-database-py](phase3-expansion-tax/040-split-database-py.md) | no | done (2026-08-10/11) | Claude | database.py 1251→749 via 2/020's extraction; DDL/registry/backfills now live in `backend/migrations/` (2026-08-11). Under the 800 gate |
| 3 | [050 frontend-hygiene](phase3-expansion-tax/050-frontend-exception-timer-hygiene.md) | no | partial — via stage2 4/030 (2026-08-11) | Claude | silent-except gate at shrinking baseline 44→40 + NiceGUI canary; timer→poll migration still open |
| 3 | [060 money-path-coverage](phase3-expansion-tax/060-money-path-coverage-floors.md) | no | done — via stage2 3/020 (2026-08-11) | Claude | broker 58.3 / runtime.py 72.2 floors in MONEY_CRITICAL_FLOORS |
| 4 | [010 ci-job](phase4-hygiene/010-ci-job.md) | no | done — activates on push (2026-08-10) | Claude/Darren | repo+remote+gitignore already exist (Q003 corrected). `.github/workflows/checks.yml` runs `tools.checks all` on Windows on push/PR + guard tests. Red/green verification happens on first push. |
| 4 | [020 test-layout](phase4-hygiene/020-test-layout-consolidation.md) | no | done — via stage2 3/030 (2026-08-11) | Claude | packages everywhere, ghost testpath gone, import-time mutation fixed, gates in tests/refactor/test_layout.py |
| 4 | [030 licence-signing](phase4-hygiene/030-licence-asymmetric-signing.md) | no | not started | — | |
| 4 | [040 docs-of-what-shipped](phase4-hygiene/040-docs-of-what-shipped.md) | no | not started | — | last task before /spec done |

## Decisions log
- Pack layout → phased by priority tier (source: user, 2026-08-08)
- Topology → single localhost-only install; security Criticals rescoped, cluster sync out of scope (source: user, 2026-08-08)
- Money anchors → SPEC-002 + SPEC-003 written before implementation (source: user, 2026-08-08)
- All six QUESTIONS.md answers → recommendations adopted **provisionally**; final decision-maker is Darren's brother, overrides possible until each consuming task is implemented (source: user, 2026-08-10)

## Verification log
Paste the real `python -m tools.checks all` output (or its tail) each time a task lands. Green
output claimed without the paste is not evidence.

- 2026-08-10, task 2/050 (backups + busy_timeout): `python -m tools.checks all` → All checks passed,
  EXITCODE=0 (all 7 gates; test suite ok 402s; coverage ratchet ok). db/backup.py + db() busy_timeout.
- 2026-08-10, task 2/020: `python -m tools.checks all` → All checks passed, EXITCODE=0 (all 7 gates;
  test suite ok 574s; coverage ratchet ok). Includes db/migrations.py + db/schema_sql.py extraction
  (database.py 1251→749) and the structure-gate data-layer classification fix.
- 2026-08-10, tasks 2/070 + 2/060: `python -m tools.checks all` → All checks passed, EXITCODE=0
  (all 7 gates; test suite 2115 tests ok 401s; coverage ratchet ok).
- 2026-08-10, task 2/010 FINAL: `python -m tools.checks all` → All checks passed, EXITCODE=0.
  structure gates ok, import contracts ok, runtime facade ok, **orphan modules ok** (new
  fail-closed gate), boot smoke ok, test suite ok (2109 passed / 7 skipped), coverage ratchet ok.
  Deferred decisions moved to docs/questions/ (answer-later queue for the brother).

- 2026-08-10, task 2/010 (partial): feeding the coverage ratchet (`--cov`) surfaced a latent
  ordering flake — `signals/repo.get_signals` ordered by `created_at DESC` (float seconds) with no
  tie-break, so same-tick signals returned oldest-first and `test_get_signals_returns_all_newest_first`
  failed non-deterministically. Fixed with a `rowid DESC` tie-break + a new test that forces the
  timestamp tie (`test_get_signals_newest_first_is_stable_on_timestamp_tie`). Read-ordering only,
  not a money path. **CONFIRMED:** `python -m tools.checks all` → "All checks passed", EXITCODE=0
  (structure/import/facade/orphan/boot ok; test suite 2109 passed, 7 skipped, 379s; coverage
  ratchet ok). Caveat: the orphan detector reads "ok" but is still the vacuous rubber stamp (scans
  deleted `forex_trader/core/`) — its redesign is the remaining part of 2/010, so this green is not
  yet *fully* honest.
- 2026-08-10, task 050: `python -m tools.checks all` → 6/7 green (structure gates, import contracts, runtime facade, orphan detector, boot smoke, full test suite 426s). Coverage ratchet FAIL — **pre-existing, not caused by this task**: "no coverage data at .coverage.json" (unfed ratchet, the exact defect phase2/010 fixes). New tests `tests/frontend/test_server_bind.py` (7) all green. Not hacked green per golden rule 4.

## Blockers / open
- QUESTIONS.md answers are provisional (recommendations adopted 2026-08-10); the brother's review may override any of them — check before implementing 1/010, 1/030, 1/060, 2/050, 2/070. His review is NOT the same thing as the money-task sign-off + demo session, which remains required per task.
- ~~Known at scaffold time: `tools.checks all` coverage step cannot pass (ratchet unfed).~~ RESOLVED 2026-08-10 by task 2/010 (coverage feed) — `tools.checks all` now goes green.
- ~~Remaining in 2/010: the orphan detector is still vacuous.~~ RESOLVED 2026-08-10: new
  `tools/refactor_audit/orphan_modules.py` (module-reachability, fails closed on missing
  entrypoints) replaces it in the gate suite; structure + import-contract gates also hardened to
  fail closed. Negative controls in `tests/refactor/test_orphan_modules.py` +
  `test_gates_fail_closed.py`. Green now genuinely means green.
- **NEW owner decision needed (phase3/010):** 4 of the 7 unreached modules are built-but-unwired
  (channels/rule_generator, breakout_signal/backtest, config/licence/client, test_signal/auth), not
  dead — each needs a wire-vs-remove call. The 3 database.py clones are superseded-dead but
  test-entangled. Nothing deleted pending those decisions. Not money-gated, but not obviously
  Darren-vs-brother either (licence/client is security/business). See orphan_module_allowlist.json.
