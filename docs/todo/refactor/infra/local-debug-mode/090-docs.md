# 090 — Docs: what actually shipped

**Status:** not started
**Depends on:** all of 010–080 (documents shipped behaviour, not intent)
**Touches money:** no
**Layer:** docs
**Leverage:** `CHANGELOG.md`, `backend/src/utils/version_history.py`, in-app About/Setup
Instructions/Glossary, `docs/system/`

## Problem

The pack adds a mode, a login, a banner, new tools and an e2e layer — all user-visible or
contributor-visible. Undocumented, the debug mode becomes folklore and the login locks Simon
out of his own app on first update.

## Decision / What to do

N/A — docs only (Tests first: N/A).

1. `CHANGELOG.md` + in-app Version History entry: debug mode, login (call out the first-run
   password step LOUDLY — this is the one behaviour change Simon hits uninvited), banner.
2. `config.yaml.example`: `debug_mode` block with a plain-English warning; note
   `FOREX_DEBUG_MODE`.
3. In-app help: Setup Instructions gains "First run: set your dashboard password" and a debug-
   mode section; Glossary entries for "Debug mode", "Simulated data"; the `frontend/app.py:456`
   security warning updated now that a login exists.
4. `docs/system/domains/`: record the new seams (broker port, signals port, debug scenarios) in
   the relevant domain READMEs; note the adapter pattern as the route for future real
   integrations (the user's stated goal: "good for future… in case we take signals from other
   places").
5. `docs/system/rules/`: if 020 introduced a formal bridge interface/Protocol, note it in
   `30-architecture.md`; add "debug mode never opens demo/live DBs" to `20-trading-safety.md`.
6. Root `README.md`: a "Run it locally without credentials" quickstart (generate debug licence
   → `FOREX_DEBUG_MODE=1 python run.py` → login `debug`/`debug`).
7. Fill the anchor spec's Verification checklist ([SPEC.md](SPEC.md)) with real evidence, and
   flip its Status. Anything in SPEC.md that must outlive the pack (the verified checklist, the
   seam design notes) moves to `CHANGELOG.md` / `docs/system/` at `/spec done` — the pack,
   SPEC.md included, is deleted on retirement and lives on in git history.

## What must NOT change

- `docs/todo/refactor/stage0/` — untouched (audit trail).
- No doc may claim behaviour that didn't ship — write from the landed code and the PROGRESS.md
  verification log, not from this pack's plans.

## Acceptance

- A cold reader (Simon) can: update, set a password, log in — and separately run the whole app
  offline following only the README quickstart.
- Anchor spec Verification checklist filled with pasted evidence.
- `python -m tools.checks all` green (docs changes can still break the boot smoke via
  config.yaml.example typos — run it anyway), output pasted into PROGRESS.md.
