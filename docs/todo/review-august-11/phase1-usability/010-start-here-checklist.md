# 010 — First-run "Start Here" checklist

**Status:** not started
**Depends on:** BAR.md agreed by Darren
**Touches money:** no (pure view-layer; reads status the app already computes)
**Layer:** frontend (+ a thin controller if new status is needed)
**Leverage:** existing status the app computes — `conn_badge` (app.py:1228), `ea_badge` (:1249),
circuit-breaker (:1533), demo/live toggle (:1503); NiceGUI `app.storage.user` (now available via the
new login's storage_secret).

## Problem

The app has no first-run flow at all (grep for `first_run|onboard|welcome` returns nothing). A new
user lands on a context-free Chart tab and cannot tell what to do. This is the owner's stated top
pain.

## Decision

A "Start Here" panel shown on first boot (and reachable from Help), gated on
`app.storage.user["setup_seen"]`. It lists the setup steps with a **live ✅/❌** each — Licence, MT5
connected, Algo enabled, Risk set, Telegram (optional), Demo-mode — and each not-done row has a
"Fix this →" button that jumps to the right Settings section. It reads existing status; it changes no
behaviour. Dismissing it sets `setup_seen`.

## What must NOT change

- No engine/order/sizing/risk behaviour. This only reads status and navigates.
- The existing pages, tabs and controls once dismissed.
- Import contracts (frontend → controllers only; if new status is needed, add a thin controller).

## Tests first (TDD)

- `tests/frontend/test_start_here.py::test_checklist_rows_reflect_status` — given fake status
  (connected/not, algo on/off…), each row shows the right ✅/❌ — behaviour
- `::test_fix_this_targets_exist` — every "Fix this →" target is a real Settings section id — wiring
- `::test_setup_seen_hides_it` — with `app.storage.user["setup_seen"]` true, the panel isn't shown;
  false → shown — boundary (+ negative control: flip the flag, panel appears)
- `::test_reads_only_no_writes` — structural: the component calls no order/close/sizing controller —
  structural

## What to do

1. Agree BAR.md (Darren). Write the tests; watch them fail.
2. Build `frontend/components/start_here.py` (first real resident of components/) — a function that
   renders the checklist from a status dict provided by the caller (testable without a live app).
3. Wire it into the app shell: show on first boot when `not app.storage.user.get("setup_seen")`;
   add a "Set up" entry to reach it again.
4. `python -m tools.checks all`.

## Where

- `frontend/components/start_here.py` — new
- `frontend/app.py` — a few-line hook to render it + the setup_seen gate (do NOT grow app.py
  meaningfully; keep the logic in the component)
- thin controller only if a status value isn't already exposed

## Acceptance

- A fresh browser session shows Start Here; each row's ✅/❌ matches real status; "Fix this →" jumps
  correctly; dismiss persists via `setup_seen`.
- **Killer test:** a non-expert can, from a cold boot, reach a working demo setup by following the
  checklist alone.
- `python -m tools.checks all` green, output in PROGRESS.md.
