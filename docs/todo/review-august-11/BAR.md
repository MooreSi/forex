# Screen bar — Usability / onboarding surfaces (phase 1)

**Status: draft — Darren must edit this and mark it `agreed` before the UI is built.**
A bar the builder wrote is not a bar. This is a first cut from the onboarding review; change
anything, then set Status to `agreed`.

Covers the new/!reworked UI surfaces in phase 1: the **Start Here checklist**, the **Help button →
Getting Started** page, **tab subtitles**, **empty states**, and the **About "Set up once / Every
day"** reframe. No money controls appear on any of these.

## Surface 1 — "Start Here" checklist (first-run + reachable from Help)

Opens: automatically on first boot (until dismissed); again via header "Set up" / Help.

| Row | Component | Live status source | Action |
|---|---|---|---|
| Licence active | NEW: components/start_here row | licence guard state | "Fix this →" Settings > Licence |
| MT5 connected | NEW row | conn_badge (app.py:1228) | "Fix this →" Settings > MT5/Bridge |
| Algorithm enabled | NEW row | ea_badge / engine state (:1249) | "Fix this →" Settings > Trading |
| Risk configured | NEW row | risk settings | "Fix this →" Settings > Risk |
| Telegram (optional) | NEW row | telegram config | "Fix this →" Settings > Telegram |
| Mode: Demo/Live | NEW row | env toggle (:1503) | inline toggle (existing) |

Strings the user reads (edit freely):
- Title: "Start here — get set up in a few steps"
- Each row done: "✓ <thing> is ready"
- Each row not done: "✗ <thing> — <one-line why it matters>  [Fix this →]"
- Dismiss: "I'm set up — don't show this again"

## Surface 2 — Help "?" button → Getting Started

Opens: a header "?" button on every screen → a Getting Started page that surfaces the existing (good,
but buried) Setup Instructions / Orchestration / Glossary content.
- Button: header, top-right, always visible. String: tooltip "Help & getting started".

## Surface 3 — Tab subtitles / renames

The 10 tabs get one-line subtitles or plainer names (AI Analysis, Chart, Trading, Parsing, Signal
Generator, Edge, Analysis, Settings, About). Darren: fill the plain-language name/subtitle per tab.

## Surface 4 — Empty states

Trading / Analysis / signals lists: replace "No signals yet" with a next-step prompt. Darren: the
exact next-step wording per surface.

## Surface 5 — About "Set up once / Every day"

Reframe the About-home nav cards into two groups: "Set up once" (install, licence, MT5, risk) and
"Every day" (what to check, how to read a signal, how to stop it). Content already exists; this
re-groups it into a path.

---
**Decision:** Status: draft. Darren edits strings/names, then sets `agreed`.
