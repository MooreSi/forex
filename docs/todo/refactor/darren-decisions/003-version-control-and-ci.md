# Q003 — Version control & CI

**Decision:** RESOLVED 2026-08-10 (corrected). `app/` **is** a git repo with a GitHub remote
(`github.com/darrenmoore/forex`), currently on branch `claude/refactor-plan-docs-pjn1hl`, and
`.gitignore` already excludes secrets (`config.yaml`, `*.db`, `*.log`, `backups/`, `.coverage.json`).
The earlier "not a repo" note referred to the parent `c:\dev\forex`, not `c:\dev\forex\app`.
**Who decides:** Darren (dev/ops).
**Consumed by:** stage1 phase4/010 (CI).

## Status

- ~~No git repo / no remote~~ — WRONG; both exist. CI is **unblocked**.
- `.gitignore` reviewed and healthy — no secret-leak risk from the remediation work (backups and
  the coverage artifact are already ignored).
- Remaining for phase4/010: add a GitHub Actions workflow running `python -m tools.checks all` on
  push/PR (Windows runner, MT5 faked as the local suite does), and set branch protection.

## Open sub-questions for Darren

1. **Commit cadence for this session's work** — a large amount of verified (green) remediation work
   is currently uncommitted on the branch. Commit it as logical checkpoints now?
   **Answer:** OVERTAKEN 2026-08-11 — the stage-2 sweep committed per phase, each with a green
   `tools.checks all` recorded in stage2/PROGRESS.md. Nothing verified sits uncommitted.
2. **Activate CI** — add `.github/workflows/checks.yml` and require it before merge to the default
   branch? (The workflow only becomes active once pushed.)
   **Answer:** workflow file exists (stage1 4/010). Still open: **push the branch** (activates CI)
   and set branch protection — Darren's call, blocks the give-to-simon checklist's "CI green" row.
