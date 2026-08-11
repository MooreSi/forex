# Phase 1 — Usability & onboarding

**Status:** not started — **recommended first move** (unblocked, pure view-layer, no money)
**Gated on:** nothing
**Touches money:** no

## Goal of this phase

A person who did not build this app — Darren today, Simon tomorrow — can open it and tell what to do.
Fixes the owner's verbatim pain: *"it's almost impossible for me to know what I'm meant to do."*
Everything here is view-only: it reads status the app already computes and adds guidance; it changes
no engine, order, sizing or risk behaviour.

## Evidence

[../../../reviews/2026-08-11/frontend-onboarding-review.md](../../../../reviews/2026-08-11/frontend-onboarding-review.md)
— no first-run flow exists anywhere; jargon tabs; good help buried behind the last tab with no Help
button; a concrete "Start Here" proposal.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-start-here-checklist.md](010-start-here-checklist.md) | First-run "Start Here" checklist with live status + "Fix this →" jumps (centerpiece) | no |
| [020-help-and-getting-started.md](020-help-and-getting-started.md) | Header Help "?" button → a Getting Started page that surfaces the buried docs | no |
| [030-tab-subtitles.md](030-tab-subtitles.md) | One-line subtitles / plain renames on the 10 jargon tabs | no |
| [040-empty-states.md](040-empty-states.md) | Turn "nothing here yet" into "do this next" prompts | no |
| [050-setup-once-every-day.md](050-setup-once-every-day.md) | Reframe About into "Set up once / Every day"; seed components/ | no |

## Exit criteria

- A first-run boot shows the Start Here checklist; a Help button is reachable from every screen.
- No jargon tab is unlabelled; empty states point to a next action.
- All new UI lives in `frontend/components/` (its first real residents), not pasted into `app.py`.
- `python -m tools.checks all` green; import contracts do not regress.
- The user-facing strings (checklist rows, tab names, empty-state prompts) are confirmed by Darren
  before the UI is built — they're his words, not the builder's guess.
