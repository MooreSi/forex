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
- Phase 3 (test remediation): not started — unblocked
- Phase 4 (frontend split): blocked — Darren must answer the restructure QUESTIONS (0/4)
- Phase 5 (debug complete): not started — 1 money task (fake-bridge wiring, Simon)
- Money-path: **moved to [stage 3](../stage3/README.md)** (Simon-gated) — not part of stage 2
- Phase 7 (handoff): in progress — HANDOFF.md done; rest not started

## Tasks

| Phase | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 1 | [010 start-here checklist](phase1-usability/010-start-here-checklist.md) | no | done (2026-08-11) | Claude (for Darren) | components/start_here.py; setup_seen gate; strings queued as docs/questions/006. Fix-this jumps land on the top-level tab (Settings sub-tab named in the hint — deep-link needs the phase-4 settings split) |
| 1 | [020 help button + getting-started](phase1-usability/020-help-and-getting-started.md) | no | done (2026-08-11) | Claude (for Darren) | components/getting_started.py + header "?"; links About sections by real ids |
| 1 | [030 tab subtitles & renames](phase1-usability/030-tab-subtitles.md) | no | done (2026-08-11) | Claude (for Darren) | components/tab_labels.py, rendered as tab tooltips; names kept (load-bearing) |
| 1 | [040 real empty states](phase1-usability/040-empty-states.md) | no | done (2026-08-11) | Claude (for Darren) | components/empty_state.py; TG-signals + 2 history surfaces + day dialog |
| 1 | [050 set-up-once / every-day](phase1-usability/050-setup-once-every-day.md) | no | done (2026-08-11) | Claude (for Darren) | components/about_home.py; About home regrouped; shares DAILY_ROUTINE with 020; shrank app.py under its LOC baseline |
| 2 | [010 numbered migration runner](phase2-proper-migrations/010-migration-runner.md) | no | done (2026-08-11) | Claude (for Darren) | db/migrations.py: 12 numbered steps (verbatim transcription), per-step version stamp, resume-from-version; database.py flat loop deleted (~215 lines) |
| 2 | [020 legacy-DB upgrade tests](phase2-proper-migrations/020-legacy-upgrade-tests.md) | no | done (2026-08-11) | Claude (for Darren) | tests/db/test_legacy_upgrade.py: base-only / stopped-at-5 / stopped-at-10 shapes reach head losslessly; negative control on the pre-flight |
| 2 | [030 retire except-pass backfills](phase2-proper-migrations/030-explicit-backfills.md) | no | done (2026-08-11) | Claude (for Darren) | db/backfills.py: 6 named every-boot backfills; missing-schema benign, all else aborts; zero except-pass left in the schema path (pinned by test) |
| 3 | [010 delete assert-nothing stubs](phase3-test-remediation/010-delete-empty-stubs.md) | no | not started | — | 13 gutted files in tests/core, twins exist |
| 3 | [020 broker+runtime coverage floors](phase3-test-remediation/020-money-coverage-floors.md) | no | not started | — | add to MONEY_CRITICAL_FLOORS |
| 3 | [030 test-layout consolidation](phase3-test-remediation/030-test-layout.md) | no | not started | — | retire tests/core, __init__.py, ghost testpaths, test_engine.py import mutation |
| 3 | [040 dedupe fixtures](phase3-test-remediation/040-fixture-dedup.md) | no | not started | — | fresh_db ×115, _FakeBridge ×69 → conftest |
| 4 | [010 drive the restructure pack](phase4-frontend-split/010-drive-restructure.md) | no | blocked | — | answer restructure QUESTIONS (Darren) first |
| 4 | [020 split settings.py / history.py / app.py](phase4-frontend-split/020-split-giant-files.md) | no | not started | — | /split-file; seed components/ |
| 4 | [030 frontend hygiene](phase4-frontend-split/030-frontend-hygiene.md) | no | not started | — | 44 silent excepts, 33 timers, canary |
| 5 | [010 fake MT5 bridge](phase5-debug-complete/010-fake-bridge.md) | YES (wiring) | not started | — | drives local-debug-mode 020; fake+tests non-money, seam Simon-gated |
| 5 | [020 fake telegram + canned news/AI/email](phase5-debug-complete/020-fakes-and-adapters.md) | no | not started | — | drives local-debug-mode 030/040 |
| 5 | [030 banner + e2e signal→close](phase5-debug-complete/030-banner-and-e2e.md) | no | not started | — | drives local-debug-mode 070/080 |
| — | money-path → [stage 3](../stage3/README.md) | YES | moved out (Simon-gated) | — | order dedup / reconciliation / halts; not stage-2 work |
| 7 | [010 HANDOFF.md](phase7-handoff/010-handoff-doc.md) | no | done (2026-08-11) | Claude/Darren | docs/todo/HANDOFF.md + questions-routing in CLAUDE.md/00-start-here |
| 7 | [020 give-to-Simon checklist](phase7-handoff/020-give-to-simon-checklist.md) | no | not started | — | the "ready?" gate |
| 7 | [030 docs & retire packs](phase7-handoff/030-docs-and-retire.md) | no | not started | — | CHANGELOG, in-app help, /spec done on finished packs |

## Decisions log
- Roadmap structure → phased, one workstream per phase, references existing packs (source: user, 2026-08-11)
- Questions-routing → docs/questions/ for Simon (source: user, 2026-08-11)

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
- Phase 4 blocked on Darren answering `docs/todo/frontend/restructure/QUESTIONS.md` (0/4).
- The money-path ([stage 3](../stage3/README.md)) + phase5/010 wiring are blocked on Simon (sign-off + demo session).
- Several debug-mode + money-path defaults already provisionally answered in stage1 and
  local-debug-mode QUESTIONS — Simon confirms.
