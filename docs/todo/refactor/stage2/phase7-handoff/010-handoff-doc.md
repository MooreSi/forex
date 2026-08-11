# 010 — HANDOFF.md + questions-routing

**Status:** done (2026-08-11) · **Touches money:** no · **Layer:** docs

## Problem

Another agent (or Simon) needs to pick this up cold, and agents kept asking Darren questions only
Simon can answer. There was no single entry point and no rule routing unanswerable questions.

## What was done (2026-08-11)

- **`HANDOFF.md`** in docs/todo/ — the money rule, who's who (Darren runs sessions; Simon holds
  creds + decides money), how to run it locally in debug mode, current state, what's parked for Simon,
  how work is tracked, and where questions go.
- **Questions-routing wired in**: `docs/system/rules/00-start-here.md` gained a "Questions you cannot
  answer go in docs/questions/" section (Simon answers); `CLAUDE.md` (always-loaded) points to
  HANDOFF.md and that rule.

## Acceptance
- ✅ A cold-start agent is told, up front, to read HANDOFF.md and to park policy/money questions in
  docs/questions/ for Simon. Keep HANDOFF.md current as phases land (update its "current state").

## Notes
Keep this DONE task as the record; update HANDOFF.md's §4 (current state) whenever a phase ships.
