# 030 — Docs of what shipped + retire finished packs

**Status:** not started · **Depends on:** the shipping phases · **Touches money:** no · **Layer:** docs

## Problem

As phases land, the user-facing docs and the knowledge base must reflect reality, and completed packs
should be retired so `docs/todo/` shows only live work.

## What to do

1. **CHANGELOG.md**: entries for what shipped — debug mode + login, localhost bind, migrations,
   backups, onboarding, etc. (trace each claim to a PROGRESS Done row).
2. **In-app help**: finalize the Getting Started / About content (phase 1) to match shipped behaviour.
3. **docs/system/**: update the affected domain files (frontend, data, engines) with what was learned;
   update the rules if any changed (fail-closed gates, cycle rule).
4. **Retire packs**: `/spec done` on `stage1` and `local-debug-mode` once their work has
   landed and `tools.checks all` is green — harvest keepers (checklist, CHANGELOG, rules) first.

## Acceptance
- CHANGELOG + in-app help + docs/system reflect shipped state; finished packs retired via `/spec done`
  with keepers harvested; `docs/todo/` shows only live work. Green suite.
