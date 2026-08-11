# 010 — Drive the frontend-restructure pack

**Status:** blocked (Darren answers the restructure QUESTIONS) · **Touches money:** no · **Layer:** frontend
**Drives:** [../../frontend/restructure/](../../frontend/restructure/README.md) — do NOT fork it.

## Problem

The 001 restructure is stalled: 0/13 tasks, 59 import-contract violations baselined, `components/`
empty, its `QUESTIONS.md` 0/4 answered. It's stalled on **Darren**, not an agent.

## What to do

1. **Darren answers `docs/todo/refactor/frontend/restructure/QUESTIONS.md`** (4 structural/naming questions).
2. Execute that pack's money-free lanes per its PROGRESS.md discipline; drive `import_contracts --check`
   from 59 toward 0 monotonically.
3. Each sub-task carries its own TDD contract in the restructure pack — follow it there.
4. `python -m tools.checks all` green after each; record in both packs' PROGRESS.

## Acceptance
- Restructure PROGRESS shows real movement; contract violations falling to 0; `components/` non-empty.
  (This task is Done when the restructure pack's money-free lanes are done.)
