# 020 — The "give-to-Simon" readiness checklist

**Status:** not started · **Depends on:** phases 1–6 landing · **Touches money:** no · **Layer:** docs

## Problem

There's no single answer to "is it ready to give to Simon?" — the risk is handing it over half-done.

## What to do

Create `docs/simon-handover/readiness-checklist.md` (a keeper doc, harvested out of this pack on `/spec done`) — a
gate that must be all-green or explicitly-deferred-with-Simon:

- [ ] Usability: a non-expert can boot debug mode and follow Start Here to a working setup (phase 1).
- [ ] Migrations: schema upgrades are numbered + legacy-shape-tested; no except-pass (phase 2).
- [ ] Tests: no assert-nothing files; broker+runtime floors; layout clean; suite trustworthy (phase 3).
- [ ] Frontend: no file over 800 lines under pages/; contract violations 0; excepts→0 (phase 4).
- [ ] Debug mode: ticks offline; e2e signal→close passes; banner shows (phase 5).
- [ ] Money-path: dedup/reconciliation/close-on-failure/halts done + **Simon-signed on a demo** (phase 6).
- [ ] Docs: HANDOFF current; CHANGELOG updated; open decisions in docs/simon-handover/ triaged.
- [ ] `python -m tools.checks all` green; CI green on the branch.

## Acceptance
- The checklist exists and is honestly filled; every unchecked item is a named, Simon-agreed deferral.
