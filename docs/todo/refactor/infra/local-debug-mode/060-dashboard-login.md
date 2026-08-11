# 060 — Dashboard login (both modes)

**Status:** not started
**Depends on:** none (independent of debug mode; ships with 070 in the same `frontend/app.py`
area)
**Touches money:** no (the page it protects contains money controls, but no order/sizing code
changes)
**Layer:** frontend + controller + service
**Leverage:** scrypt helpers `services/cluster/remote/auth.py:30,40,55` (+ their tests);
NiceGUI auth middleware pattern (`app.storage`, `storage_secret`)

## Problem

The dashboard has no authentication at all — `frontend/app.py:709` serves everything to anyone
on port 8888, `ui.run` has no `storage_secret` (`run.py:262-277`), and the app's own help text
warns about it (`frontend/app.py:456`). Darren needs credentials for local/e2e work; Simon's
machine ships with an open control panel that can move real money.

## Decision

Single-user username/password:

- `backend/src/services/auth/` (new small service): scrypt hash storage in the user data dir
  (reuse/adapt `remote/auth.py`'s functions — extract shared helpers rather than copy),
  `verify(username, password)`, `is_set()`, session-token issue/check.
- `backend/src/controllers/auth_controller.py` — thin: login/logout/first-run-set forwarding to
  the service.
- Frontend: NiceGUI middleware gating **all** routes (not per-page), `storage_secret` in
  `ui.run`, a login page and a first-run setup page per [BAR.md](BAR.md) (which Darren must
  edit to `agreed` before the UI is built), "Sign out" in the power dialog.
- Debug mode only: if no hash exists, seed `debug`/`debug` (QUESTIONS.md #3) so e2e and local
  boots need no manual step. Never seeded when debug is off.
- Licence screens (guard's own pages on 8888) stay outside the gate — they run pre-app.

## What must NOT change

- Zero behaviour change once authenticated: every page, timer and control as today.
- The four import contracts (frontend→controllers only; controller thin, no loops/merges).
- `remote/auth.py`'s existing behaviour + its tests pass unmodified if helpers are extracted.

## Tests first (TDD)

- `tests/controllers/test_auth_controller.py::test_login_roundtrip` — set → verify ok; wrong
  password rejected — behaviour (+ negative control both directions)
- `::test_first_run_requires_setup` — no hash → setup required state — behaviour
- `::test_lockout_after_failed_attempts` — 5 fails → locked 60s (starting values) — boundary
- `tests/core/test_auth_service.py::test_hash_never_stores_plaintext` — file on disk contains
  no plaintext — boundary
- `tests/frontend/test_login_gate.py` (or the suite's existing frontend-test idiom — check
  `tests/` layout first): unauthenticated request to `/` → login; authenticated → dashboard —
  wiring
- `::test_debug_seed_only_in_debug` — seed happens iff `is_debug()` — wiring (+ negative
  control)

## What to do

1. **BAR.md first**: Darren edits and marks `agreed`. Do not build the UI against the draft.
2. Write the tests; watch them fail.
3. Service + controller; extract shared scrypt helpers so `remote/auth.py` and dashboard auth
   share one implementation.
4. Frontend middleware + pages. `frontend/app.py` is 1633 lines — put the new UI in its own
   page module per `/frontend-conventions`, do NOT grow `app.py`; if the middleware hook must
   live there, keep it to a few lines.
5. `tools/set_dashboard_password.py` — CLI setter/reset for headless machines.
6. `python -m tools.checks all`.

## Where

- `backend/src/services/auth/` — new
- `backend/src/controllers/auth_controller.py` — new
- `frontend/pages/login/` (per frontend conventions) + minimal hook in `frontend/app.py` /
  `run.py:262` (`storage_secret`)
- `tools/set_dashboard_password.py` — new

## Acceptance

- Fresh boot, debug off: first load demands password setup; thereafter every route requires
  login; wrong password rejected with no username/password distinction.
- Debug boot: `debug`/`debug` works with zero manual setup.
- **The killer test:** the middleware wiring test — an unauthenticated hit on any route never
  renders dashboard content.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

`storage_secret` must be stable across restarts (persist a generated secret in the user data
dir) or every update logs Simon out. Session lifetime 7 days (starting value). Never log
credentials.
