# Phase 4 — Frontend split & restructure

**Status:** blocked — Darren must answer the restructure QUESTIONS (0/4) first
**Gated on:** `docs/todo/frontend/restructure/QUESTIONS.md` answered
**Touches money:** no

## Goal of this phase

The giant frontend files are split and the stalled restructure is finished. Owner note: *"Frontend
needs to be split, large files."* `settings.py` is 3,112 lines; `history.py` 1,416; `app.py` 1,633.
The 001 restructure is 0/13 with 59 import-contract violations and an empty `components/`; silent
excepts regressed 31→44. This phase **drives the existing restructure pack** rather than duplicating
it, and folds in review-august-08 phase3's frontend hygiene.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-drive-restructure.md](010-drive-restructure.md) | Answer the restructure QUESTIONS, then execute its money-free lanes; drive 59→0 contract violations | no |
| [020-split-giant-files.md](020-split-giant-files.md) | `/split-file` settings.py / history.py / app.py into packages; seed components/ with shared helpers | no |
| [030-frontend-hygiene.md](030-frontend-hygiene.md) | Replace the 44 silent excepts + 33 blocking timers; add the NiceGUI monkey-patch upgrade canary | no |

## Drives / references

- [../../frontend/restructure/](../../frontend/restructure/README.md) — the 001 pack (do not fork).
- [../../review-august-08/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md](../../review-august-08/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md).

## Exit criteria

- `import_contracts --check` reports 0 (from 59); no file over 800 lines under frontend/pages/;
  `components/` populated; excepts/timers count down with a fail-closed AST guard.
- `python -m tools.checks all` green.
