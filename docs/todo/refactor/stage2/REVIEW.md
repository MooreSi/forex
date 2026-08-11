# Road to handoff — evidence

This roadmap is grounded in reviews, not guesses. Each phase points at its evidence:

| Phase | Evidence |
|---|---|
| 1 Usability | [../../reviews/2026-08-11/frontend-onboarding-review.md](../../../reviews/2026-08-11/frontend-onboarding-review.md) — no first-run flow exists anywhere (grep for first_run/onboard/welcome → nothing); 10 jargon tabs, no subtitles; good docs buried behind the last tab, no Help button; confetti for profit but nothing for a lost newcomer. Includes the concrete "Start Here" proposal. |
| 2 Proper migrations | Owner note (`docs/todo/notes.md`: "Proper migrations, not all in the database.py") + stage1 phase2/020 (the fail-closed core already landed; the numbered-runner refinement was explicitly deferred there). |
| 3 Test remediation | [../../reviews/2026-08-11/testing-design-review.md](../../../reviews/2026-08-11/testing-design-review.md) — 13 gutted characterization files in tests/core (docstring/fixtures but zero `def test_`, twins exist → delete); money floors omit broker (58.3%) + runtime.py (72.2%); layout off-protocol (tests/core 124 files, missing __init__.py, frontend/tests ghost, test_engine.py import-time mutation); fixture sprawl (fresh_db ×115, _FakeBridge ×69). Also confirms the guardrails I rebuilt are genuinely real. |
| 4 Frontend split | frontend-onboarding-review (restructure stalled 0/13, 59 contract violations, components/ empty, silent excepts regressed 31→44) + stage1 phase3 + `docs/todo/refactor/frontend/restructure/`. Owner note: "Frontend needs to be split, large files." |
| 5 Debug complete | `docs/todo/refactor/infra/local-debug-mode/` (SPEC + tasks; 010 config + login done this session). |
| Money-path (→ [stage 3](../stage3/README.md)) | [../../reviews/2026-08-08/risk-review.md](../../../reviews/2026-08-08/risk-review.md) — the specced order-dedup / reconciliation / halts work, extracted to stage 3 (Simon-gated). |
| 7 Handoff | This session — HANDOFF.md written, questions-routing wired into CLAUDE.md + 00-start-here.md. |

**Method note:** the two 2026-08-11 reviews were read-only (no app run, no MT5, no DB writes). The
onboarding finding is from the owner directly running the app and reporting he couldn't tell what to
do — the strongest evidence there is.
