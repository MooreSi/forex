# 070 — Auto-update channel off by default until signed

**Status:** not started
**Depends on:** none
**Touches money:** no
**Layer:** service + config
**Leverage:** config default mechanism; nothing new is built — this fix is subtraction

## Problem

The remote update channel is an unauthenticated code-execution path (review security C2):
`remote/client.py:504-668` accepts a pushed ZIP written over the app and run; integrity is a
SHA-256 sent in the same message; TLS verification is `CERT_NONE` (`remote/tls.py:90-95`); the
server is discovered by an unauthenticated UDP LAN beacon + subnet scan; the update path also runs
`pip install` from a requirements.txt inside the ZIP. Owner confirms single-node localhost
deployment — nothing legitimate currently needs this channel.

## Decision

Default the auto-update client (and its UDP discovery listener) to **disabled**; enabling requires
an explicit config key whose docstring states plainly that the channel is unauthenticated. Chosen
over hardening now (days of signing/pinning work with no current consumer) and over deleting the
code (the big vision may want it — hardening becomes its own future pack when distribution starts).
Per QUESTIONS.md #5 — this task implements the "disable now, decide later" recommendation unless
the answer says otherwise.

## What must NOT change

- The update code itself — not deleted, not refactored; only its activation.
- Manual/installer-based updating — untouched.
- The sync channel is out of this task's scope (its cert-pinning gap is noted for the future
  security pack; single-node means it has no live peer today).

## Tests first (TDD)

- `tests/cluster/test_update_disabled.py::test_update_client_not_started_by_default` — default
  config boots no update client task and no UDP listener — surface
- `::test_explicit_enable_starts_it` — negative control: the flag genuinely gates it — control
- `::test_enable_logs_unauthenticated_warning` — enabling emits the loud warning — wiring
- `::test_no_network_listeners_by_default` — structural: default boot's registered runtime tasks
  contain no discovery/update entries — structural

## What to do

1. Confirm QUESTIONS.md #5 answer (default path assumed: disable).
2. Write the tests above; run them; confirm they fail for the right reason.
3. Add the config key (default off); gate client startup + UDP listener registration on it.
4. Loud warning on explicit enable; note in setup text.
5. `python -m tools.checks all`.

## Where

- `backend/src/services/cluster/remote/client.py` — startup gating
- config schema — the key
- `frontend/pages/update_panel.py` — show "disabled" state honestly rather than a dead panel

## Acceptance

- Default boot: netstat-equivalent in tests shows no update/discovery listener; update panel says
  disabled and why.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- The future hardening pack (when distribution starts) needs: asymmetric-signed update manifests,
  pinned server cert, no LAN discovery, no in-ZIP pip install. Parked, not forgotten — referenced
  in the pack README's out-of-scope.
