# Frontend restructure — phase 3: write it down

**Status:** not started
**Gated on:** phases 1 and 2 complete — this phase describes what shipped, not what was intended.
**Touches money:** no

## Goal of this phase

Two things outlive this pack, and neither is code:

1. **The conventions** — where components go, and what the closed controller boundary means for
   anyone adding a page. Without this written into `docs/system/rules/`, the next feature reintroduces exactly
   what phases 1 and 2 removed, and the pack's deletion takes the reasoning with it.
2. **The React decision and its reasons** — so it is re-decided on evidence in a year, not
   re-litigated from scratch every time someone notices the frontend is Python.

The pack itself is deleted at `/spec done`. This phase is what remains.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-conventions.md](010-conventions.md) | `docs/system/rules/` updates, the exemption register, CHANGELOG, and the React decision record | no |

One task: the work is a single coherent write-up and splitting it would produce cross-referencing
fragments.

## Note on user-facing docs

This pack changes **nothing** a user sees — no new setting, no moved button, no changed label. So
unlike most packs there is no in-app help to update: the About, Setup Instructions and Glossary pages
are correct before and after. `app.py`'s About content *moves* in task 2/040, but its text is
required to be byte-identical.

The CHANGELOG entry is therefore an internal one. Say what changed structurally and that behaviour is
unchanged; do not manufacture a user-facing benefit that does not exist.

## Exit criteria

- `docs/system/rules/70-file-organisation.md` documents the component convention, validated against five real
  pages rather than one.
- `docs/system/rules/30-architecture.md` records the frontend→controllers contract as enforced at zero,
  alongside the other four.
- Every surviving over-800 file has its exemption reason recorded where the gate's reader will find
  it.
- The React decision is recorded with its reasoning and the conditions under which it should be
  revisited.
- CHANGELOG entry written.
- `docs/specs/001-frontend-restructure.md` Verification checklist filled in, Status → Shipped.
- `python -m tools.checks all` green.
