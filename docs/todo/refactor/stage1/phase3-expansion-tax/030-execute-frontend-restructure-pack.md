# 030 — Unblock and execute the existing frontend-restructure pack

**Status:** not started
**Depends on:** none (its own pack defines internal ordering)
**Touches money:** no in *this* task — but the delegated pack's trading task (its 1/020) is
money-touching and governed **there**, under `/safe-change`, with its own sign-off + demo session.
**Layer:** frontend
**Leverage:** the whole point — the pack at [docs/todo/refactor/frontend/restructure/](../../frontend/restructure/)
already exists, anchored on [docs/specs/001-frontend-restructure.md](../../frontend/restructure/README.md).
This pack extends, never forks.

## Problem

The restructure was specced and never started (review frontend #1): 0 of 13 tasks begun, the
import contract still at 59 violations (verified 2026-08-08 via `import_contracts --check`),
`components/` empty, its QUESTIONS.md 0/4 answered — which already blocks its app-shell task. The
worst violations are money-adjacent: `history.py:16-19` imports repo modules and private runtime
money math (`_apply_fee`, `_platform_fee_rate`); `settings.py` (3,112 lines) embeds MT5-bridge
subprocess lifecycle in the view (lines 1759-2282).

## Decision

This task is a *pointer with a sequence*, not a copy: drive the existing pack per the review's
recommended order — owner answers its QUESTIONS.md; run the money-free lanes first (its tasks
010/030/040); its money-touching trading task (1/020) ships alone with characterization tests + a
demo session; then the settings.py split and seeding `components/` with the duplicated
format/poll helpers (`_fmt_ts`/`_dir_color`/`_pnl_color`/`_safe_refresh`, already drifted across
three panels). All detail lives in that pack's own task files.

## What must NOT change

- Governed by SPEC-001's own "what must NOT change" — this file adds nothing and overrides
  nothing.
- No parallel restructure work happens in *this* pack's tree — one pack owns the frontend.

## Tests first (TDD)

- N/A here — each delegated task carries its own TDD contract in the restructure pack. This task
  is Done when the delegated pack's PROGRESS.md shows the listed lanes done, not when any test in
  *this* pack passes.

## What to do

1. Owner answers `docs/todo/refactor/frontend/restructure/QUESTIONS.md` (4 open; blocks app-shell).
2. Execute its money-free lanes 010/030/040 per its PROGRESS.md discipline.
3. Its trading task 1/020 alone: `/safe-change`, characterization tests, demo session, sign-off.
4. settings.py split (`/split-file`; the review found clean `_render_*` seams for a 9-module
   `components/settings/` split) and seed `components/` with the shared helpers.
5. Keep the 59-violation import-contract count falling monotonically; it ends at zero.

## Where

- everything under `docs/todo/refactor/frontend/restructure/` and the files its tasks name

## Acceptance

- The restructure pack's own PROGRESS.md shows the four lanes done; `import_contracts --check`
  reports 0 (from 59); `components/` is non-empty and the three drifted helper copies are gone.
- `python -m tools.checks all` green, output pasted into **both** packs' PROGRESS.md.

## Notes

- If the restructure pack's plan conflicts with anything this remediation pack changed (e.g.
  UNKNOWN state display from phase1/020), the restructure pack updates its files — recorded there,
  referenced here.
