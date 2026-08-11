# Road to handoff — PROGRESS

**Shared status log across all phases. Any agent picking up a task updates this file** — claim a row
(name + date under Owner), flip its Status, leave a one-line Note (commit / blocker / decision). A
task reported Done that isn't is the exact failure this repo's rules exist to prevent.

_Last updated: 2026-08-11 — phase 1 (usability) complete and verified green._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

A money-touching task is **not** `done` on a green suite alone — it needs Simon's sign-off + a demo
session, both recorded in Notes.

## Overall
- Phase 1 (usability): **done** (2026-08-11) — all five tasks, TDD, checks green
- Phase 2 (proper migrations): **done** (2026-08-11) — registry, legacy fixtures, explicit backfills
- Phase 3 (test remediation): **done** (2026-08-11) — stubs deleted+gated, floors set, layout fixed+gated, fixtures deduped to a shrinking baseline
- Phase 4 (frontend split): in progress — unblocked (provisional answers); engine-panel lane done (contract 59→50), hygiene gates landed; splits + remaining lanes open
- Phase 5 (debug complete): **done except the `_make_bridge` seam** (2026-08-11) — fakes, guards, banner and the offline e2e all landed; the 3-line seam edit + run.py subprocess skip await Simon (sign-off + demo)
- Money-path: **moved to [stage 3](../stage3/README.md)** (Simon-gated) — not part of stage 2
- Phase 7 (handoff): in progress — HANDOFF.md done; rest not started

## Tasks

| Phase | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 1 | [010 start-here checklist](phase1-usability/010-start-here-checklist.md) | no | done (2026-08-11) | Claude (for Darren) | components/start_here.py; setup_seen gate; strings queued as docs/todo/refactor/darren-decisions/006-onboarding-strings.md. Fix-this jumps land on the top-level tab (Settings sub-tab named in the hint — deep-link needs the phase-4 settings split) |
| 1 | [020 help button + getting-started](phase1-usability/020-help-and-getting-started.md) | no | done (2026-08-11) | Claude (for Darren) | components/getting_started.py + header "?"; links About sections by real ids |
| 1 | [030 tab subtitles & renames](phase1-usability/030-tab-subtitles.md) | no | done (2026-08-11) | Claude (for Darren) | components/tab_labels.py, rendered as tab tooltips; names kept (load-bearing) |
| 1 | [040 real empty states](phase1-usability/040-empty-states.md) | no | done (2026-08-11) | Claude (for Darren) | components/empty_state.py; TG-signals + 2 history surfaces + day dialog |
| 1 | [050 set-up-once / every-day](phase1-usability/050-setup-once-every-day.md) | no | done (2026-08-11) | Claude (for Darren) | components/about_home.py; About home regrouped; shares DAILY_ROUTINE with 020; shrank app.py under its LOC baseline |
| 2 | [010 numbered migration runner](phase2-proper-migrations/010-migration-runner.md) | no | done (2026-08-11) | Claude (for Darren) | db/migrations.py: 12 numbered steps (verbatim transcription), per-step version stamp, resume-from-version; database.py flat loop deleted (~215 lines) |
| 2 | [020 legacy-DB upgrade tests](phase2-proper-migrations/020-legacy-upgrade-tests.md) | no | done (2026-08-11) | Claude (for Darren) | tests/db/test_legacy_upgrade.py: base-only / stopped-at-5 / stopped-at-10 shapes reach head losslessly; negative control on the pre-flight |
| 2 | [030 retire except-pass backfills](phase2-proper-migrations/030-explicit-backfills.md) | no | done (2026-08-11) | Claude (for Darren) | db/backfills.py: 6 named every-boot backfills; missing-schema benign, all else aborts; zero except-pass left in the schema path (pinned by test) |
| 3 | [010 delete assert-nothing stubs](phase3-test-remediation/010-delete-empty-stubs.md) | no | done (2026-08-11) | Claude (for Darren) | 13 stubs deleted (each surface twin verified populated, 5–25 tests); gate tests/refactor/test_no_empty_test_files.py enforces the class at zero |
| 3 | [020 broker+runtime coverage floors](phase3-test-remediation/020-money-coverage-floors.md) | no | done (2026-08-11) | Claude (for Darren) | broker 58.3 / runtime.py 72.2 added to MONEY_CRITICAL_FLOORS at measured values; negative control added |
| 3 | [030 test-layout consolidation](phase3-test-remediation/030-test-layout.md) | no | done (2026-08-11) | Claude (for Darren) | reversal_engine __init__.py; frontend/tests ghost dropped from testpaths + deleted; test_engine.py/test_signal_parser.py import-time mutation moved to a fixture / removed; gate tests/refactor/test_layout.py; collected count 1998 unchanged. Bulk tests/core-to-mirror move noted as follow-up, not done |
| 3 | [040 dedupe fixtures](phase3-test-remediation/040-fixture-dedup.md) | no | done (2026-08-11) | Claude (for Darren) | 35 byte-equivalent fresh_db copies migrated to conftest (517 tests in touched files green); remaining 66 fresh_db / 56 _FakeBridge under a shrinking baseline (tests/refactor/test_fixture_dedup.py) + no-MetaTrader5-import guard. Full 66→1 migration is follow-up (variants differ for real) |
| 4 | [010 drive the restructure pack](phase4-frontend-split/010-drive-restructure.md) | no | in progress (2026-08-11) | Claude (for Darren) | QUESTIONS answered provisionally (unblocked); restructure phase1/010 DONE: engines_controller lifecycle ops, 5 files rewired, contract 59→50, baseline tightened to 50. Lanes 030/040/050/060 and phase-2 splits remain; 020 (trading & risk) is the money task — Simon-gated, untouched |
| 4 | [020 split settings.py / history.py / app.py](phase4-frontend-split/020-split-giant-files.md) | no | not started | — | /split-file; needs its own session — settings.py alone is 3,112 lines of verbatim moves |
| 4 | [030 frontend hygiene](phase4-frontend-split/030-frontend-hygiene.md) | no | partially done (2026-08-11) | Claude (for Darren) | NiceGUI canary landed (patches verified on 3.15); silent-except AST gate at a shrinking baseline 44→40 (4 header-refresh swallows now logged, incl. the whole-header one); timer→poll-helper migration NOT done (33 timers remain — follow-up) |
| 5 | [010 fake MT5 bridge](phase5-debug-complete/010-fake-bridge.md) | YES (wiring) | done except the Simon-gated seam (2026-08-11) | Claude (for Darren) | services/broker/fake_market.py + fake_bridge.py: full 21-name surface (introspection-pinned vs BOTH real clients), deterministic curve + JSON scenarios (tools/debug_scenarios/), ledger with server-side SL/TP settle, error injection. **`_make_bridge` NOT edited** — guarded by test_make_bridge_debug.py until Simon's sign-off + demo. Tests in tests/services/broker/ (NOT tests/core — that dir is closed) |
| 5 | [020 fake telegram + canned news/AI/email](phase5-debug-complete/020-fakes-and-adapters.md) | no | done (2026-08-11) | Claude (for Darren) | services/telegram/fake_reader.py through the REAL scan/parser (killer test green); composition-root swap in backend/src/app._make_tg_reader; is_debug() guards: alerts, bot loop, news_calendar + news_filter (canned event 2h out), AI complete/vision/RSS/model-refresh, email. Each with a debug-off negative control |
| 5 | [030 banner + e2e signal→close](phase5-debug-complete/030-banner-and-e2e.md) | no | done (2026-08-11) | Claude (for Darren) | components/debug_banner.py behind the shell's is_debug() gate; tests/e2e/test_signal_to_close.py drives scripted signal → parser → auto-execute → fake ledger → monitor TP1 partial + BE move → frozen close path records the close (profit AND SL-loss paths). Deviation: drives the runtime facade directly rather than booting app.startup()'s task supervisors |
| — | money-path → [stage 3](../stage3/README.md) | YES | moved out (Simon-gated) | — | order dedup / reconciliation / halts; not stage-2 work |
| 7 | [010 HANDOFF.md](phase7-handoff/010-handoff-doc.md) | no | done (2026-08-11) | Claude/Darren | docs/todo/refactor/HANDOFF.md + questions-routing in CLAUDE.md/00-start-here |
| 7 | [020 give-to-Simon checklist](phase7-handoff/020-give-to-simon-checklist.md) | no | done (2026-08-11) | Claude (for Darren) | docs/simon-handover/readiness-checklist.md — honestly filled: green on phases 1/2/3/5-except-seam + docs; open on phase 4, stage-3 money-path, CHANGELOG-was-open-now-done, CI-push |
| 7 | [030 docs & retire packs](phase7-handoff/030-docs-and-retire.md) | no | partially done (2026-08-11) | Claude (for Darren) | CHANGELOG "Unreleased — Road to Handoff" section added; domain files (data/broker/frontend) updated as work landed; in-app help IS the shipped phase-1 content. NOT retired: stage1 (remainder open) and local-debug-mode (seam + 090 open) — retiring an unfinished pack would falsify docs/todo |

## Decisions log
- Roadmap structure → phased, one workstream per phase, references existing packs (source: user, 2026-08-11)
- Questions-routing → docs/simon-handover/ for Simon (source: user, 2026-08-11)

## Verification log
Paste the real `python -m tools.checks all` output (or its tail) each time a task lands.

- 2026-08-11 — phase 1 (all five tasks):
  ```
  structure gates        ok   (5.2s)
  import contracts       ok   (5.9s)
  runtime facade         ok   (0.3s)
  orphan modules         ok   (4.6s)
  boot smoke             ok   (5.2s)
  test suite             ok   (395.7s)
  coverage ratchet       ok   (0.3s)
  All checks passed.
  ```
- 2026-08-11 — phase 5 (fakes, debug guards, banner, e2e) + phase 7 docs:
  ```
  structure gates        ok   ·  import contracts  ok  ·  runtime facade  ok
  orphan modules         ok   ·  boot smoke        ok
  test suite             ok   (450.0s)
  coverage ratchet       ok   (0.3s)
  All checks passed.
  ```
- 2026-08-11 — phase 3 (stub deletion + gates, floors, layout, fixture dedup):
  ```
  structure gates        ok   ·  import contracts  ok  ·  runtime facade  ok
  orphan modules         ok   ·  boot smoke        ok
  test suite             ok   (313.5s)
  coverage ratchet       ok   (0.2s)
  All checks passed.
  ```
- 2026-08-11 — phase 2 (migration registry + backfills + legacy fixtures):
  ```
  structure gates        ok   (6.2s)
  import contracts       ok   (4.8s)
  runtime facade         ok   (0.2s)
  orphan modules         ok   (2.1s)
  boot smoke             ok   (5.3s)
  test suite             ok   (346.5s)
  coverage ratchet       ok   (0.3s)
  All checks passed.
  ```

## Blockers / open
- Phase 4 UNBLOCKED 2026-08-11: the 4 restructure QUESTIONS answered provisionally (each with its
  own recommendation, marked PROVISIONAL inline) — Darren confirms or overrides.
- The money-path ([stage 3](../stage3/README.md)) + the phase5/010 `_make_bridge` seam are blocked
  on Simon (sign-off + demo session). Everything else in phase 5 has landed.
- Provisional answers awaiting confirmation: stage1 + local-debug-mode QUESTIONS (Simon),
  restructure QUESTIONS + onboarding strings `docs/todo/refactor/darren-decisions/006-onboarding-strings.md` (Darren).
- CI activates only on first push; no remote configured yet (docs/todo/refactor/darren-decisions/003-version-control-and-ci.md).
