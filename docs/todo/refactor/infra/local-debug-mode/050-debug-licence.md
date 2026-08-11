# 050 — Debug licence: a valid local key, guard untouched

**Status:** not started — **blocked on QUESTIONS.md #1 (Simon's sign-off)**
**Depends on:** 010-debug-config.md
**Touches money:** no
**Layer:** tools
**Leverage:** `config/licence/keygen.py:21 generate_licence_key`, `store.py` key file,
`fingerprint.py` machine id

## Problem

`run.py:219 guard.enforce()` runs before anything else and exits (via its own NiceGUI error
page) without a valid key. Darren has no key. The golden rules forbid adding "a licence or auth
bypass, even for testing" — so no skip flag, no guard edit, no `if is_debug(): return`.

## Decision

`tools/generate_debug_licence.py`: computes this machine's fingerprint, calls the existing
`generate_licence_key(machine_id, expiry)` with a 30-day expiry (starting value), writes the
store file the same way the registration flow does, prints what it did and when the key dies.
`enforce()` then passes on its own, untouched logic. The tool refuses to run unless
`FOREX_DEBUG_MODE=1`, purely as a speed bump, and its docstring states the security reality
(the secret ships in the repo — this tool adds no new exposure, it documents existing exposure).

## What must NOT change

- Anything under `backend/src/config/licence/` — zero edits. That is the whole point.
- The store-file format and location.

## Tests first (TDD)

- `tests/tools/test_generate_debug_licence.py::test_generated_key_passes_real_verifier` — key
  from the tool verifies via `keygen.verify_licence_key` and matches this machine's
  fingerprint — behaviour
- `::test_expiry_is_bounded` — expiry ≤ 30 days out — boundary
- `::test_refuses_without_debug_env` — exits nonzero, writes nothing — boundary (+ negative
  control: with the env it does write to a tmp store path)
- `::test_guard_module_untouched` — structural guard: no import of the tool from
  `backend/src/**`, and (belt-and-braces) the pack's diff for this task contains no
  `config/licence/` changes — verified by review rather than a test if a test is impractical;
  say so in PROGRESS.md.

## What to do

1. Get the ANSWER on QUESTIONS.md #1 recorded first. If Simon prefers issuing a key himself,
   this task collapses to documentation (090) — mark it deferred, don't build it anyway.
2. Write the tests (point the store path at tmp via env/monkeypatch — never the real
   `~/.forex_trader_licence` from tests); watch them fail.
3. Implement the tool.
4. Also confirm-by-test that a debug boot leaves cluster surfaces off: remote admin client
   (`remote_admin_client_enabled` default False), sync server (DB-gated), — one wiring test
   `tests/core/test_app_wiring_debug.py::test_cluster_stays_off_in_debug`.
5. `python -m tools.checks all`.

## Where

- `tools/generate_debug_licence.py` — new
- `tests/tools/test_generate_debug_licence.py` — new

## Acceptance

- Fresh machine, `FOREX_DEBUG_MODE=1`: run the tool once, then `python run.py --no-browser`
  passes the licence gate with **no** edits under `config/licence/`.
- **The killer test:** `test_generated_key_passes_real_verifier`.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

Never commit a generated key or the store file. The 30-day expiry is a starting value —
`/add-tunable` does not apply (this is a dev tool, not app behaviour).
