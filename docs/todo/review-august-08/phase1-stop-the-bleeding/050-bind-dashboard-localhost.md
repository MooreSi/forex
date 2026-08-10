# 050 — Bind the dashboard to localhost

**Status:** not started
**Depends on:** none
**Touches money:** no (but it guards everything that does)
**Layer:** frontend (serving config)
**Leverage:** `run.py` already centralises server startup

## Problem

The dashboard — which can place/close live orders and edit every risk setting — serves on
`0.0.0.0:8888` with no authentication (`run.py:262-277`, review security C1). Owner confirms the
deployment is single-machine localhost-only, so nothing legitimate uses the network exposure.

## Decision

Bind to `127.0.0.1` by default, with a config override (`server.host`) for the future networked
deployment — which per the pack decisions will not be enabled until real authentication exists.
Chosen over adding auth now because auth for a single-user localhost app is dead weight; the bind
is one line and closes the LAN hole today.

## What must NOT change

- Port stays 8888; every localhost workflow (`http://localhost:8888`, the .command/.bat launchers)
  works identically.
- No auth/licence code touched — this is only the listen address.

## Tests first (TDD)

- `tests/frontend/test_server_bind.py::test_default_host_is_loopback` — the resolved serve config
  is `127.0.0.1` by default — surface
- `::test_host_override_requires_explicit_config` — only an explicit `server.host` changes it — wiring
- `::test_bind_detector_can_fail` — negative control: with a planted `0.0.0.0` config the assertion
  fails — control

(Assert on the resolved config passed to the server, not by opening real sockets — boot smoke
already proves serving works.)

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Change the default host in `run.py:262-277` (and any duplicate default in `backend/src/app.py`)
   to `127.0.0.1`; thread `server.host` through config with that default.
3. Check the setup text at `frontend/app.py:456` ("it has no separate login of its own") still
   reads true and note the localhost-only default there.
4. `python -m tools.checks all` (boot smoke must still pass).

## Where

- `run.py` — default bind
- `backend/src/app.py` — if it carries its own default
- `frontend/app.py:456` — setup text touch-up

## Acceptance

- Fresh start serves on 127.0.0.1:8888; another machine on the LAN gets connection refused.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- When the big vision networks this app, the deferred work is: real login + TLS *before* the bind
  is widened. That future task should live in a security pack; the config override here must not
  become a silent footgun — log a prominent warning if `server.host` is non-loopback.
