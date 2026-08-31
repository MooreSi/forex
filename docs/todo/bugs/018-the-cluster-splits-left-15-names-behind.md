# 018 — the cluster splits left 15 names behind

**Found:** 2026-08-31
**Fixed:** 2026-08-31, same day
**Introduced:** 2026-08-30, by me, in commit `6e85e6d` and the sync splits alongside it
**Severity:** one of them ran on every successful remote client connection

## What happened

Four files were split out of `cluster/remote/server.py` and `cluster/sync/server.py`
to bring them under the 800-line ceiling. The moves were verbatim and the
callers were updated. **Fifteen names the moved code depended on stayed
behind**, in the modules they were moved out of.

| File | Names left behind |
|---|---|
| `remote/_beacon_version.py` | `_CHANGELOG_FILE`, `SERVER_PORT` |
| `sync/_telemetry.py` | `make`, `MSG_STATUS_HEARTBEAT`, `MSG_SIGNAL_GEN_STATS`, `TRADER_REMOTE_VPS`, and the five heartbeat/liveness intervals |
| `sync/_peer_data.py` | `Optional` |
| `sync/_server_peer_data.py` | `Optional` |

Every one raises `NameError` the moment its line executes.

## Why it mattered

`_read_changelog()` is called on **every successful client connection**. The
welcome sequence is MSG_WELCOME, then the licence if there is one, then
MSG_VERSION_INFO carrying the changelog. So a client would have been welcomed
and licensed, and the connection would then have died before it learned what
version to update to — with the failure appearing at the version step, nowhere
near the split that caused it.

`_lan_beacon_loop()` raises on its first iteration, so LAN discovery is dead
and clients fall back to the WAN IP, which is exactly what the beacon exists to
avoid (NAT hairpinning).

The `_telemetry` names break the VPS heartbeat and the liveness watchdog — the
mechanism by which the Mac learns the VPS has gone quiet.

## Why nothing caught it

`python -m tools.checks all` was **8/8 green** for both splits and every commit
after them. Nothing in the repo looked for undefined names, the boot smoke only
imports the composition root (an undefined name inside a function body is not
an import error), and coverage in the four files was 17–27%.

This is the fourth time this repo has had this exact bug — see
[010](010-test-panel-reset-params-nameerror.md) (undefined `ap`) and
[011](011-signal-generator-analysis-nameerror.md) (undefined
`_SIGNAL_GEN_SYSTEM`). Both of those were also found by reading, not by a test.

## The fix

Names restored to the modules that use them, choosing the option that does not
create an import cycle in each case:

- `_CHANGELOG_FILE` → resolved per call inside `_read_changelog` (importing it
  back from `server.py` would be circular)
- `SERVER_PORT` → imported from `remote/tls.py`, the one definition
- the five interval constants → **moved** to `_telemetry.py`, whose loops are
  their only readers; `server.py` no longer defines them
- protocol names and `Optional` → ordinary imports

Behaviour tests for the two worst
(`tests/remote/test_update_application.py::TestTheBeaconAndVersionHelpersActuallyRun`),
because a name resolving is not the same as a function working.

## The gate

`tools/refactor_audit/undefined_names.py`, now the fifth check in
`python -m tools.checks all`. Stdlib only — pyflakes would do this and more but
is not a declared dependency of this project, and a scanner does not get to add
one.

Validated by comparing its output against pyflakes 3.4.0 across the whole tree:
**identical, 15 for 15**. That comparison is kept as a test that skips where
pyflakes is not installed, so it never becomes a back-door dependency.

`tests/refactor/test_undefined_names.py` carries 22 negative controls — sixteen
legitimate constructs that must NOT be reported (comprehensions, walrus,
conditional imports, `global`, closures, lambda params, except-as, for-else),
plus the class-scope rule in both directions, plus a planted bug it must catch.
A scanner with false positives gets its gate switched off, which is worse than
having no gate.

## What to take from it

The `/split-file` procedure said to check for module-level `global` state
before splitting. It did not say to check that the code you moved can still
see everything it uses. It does now, and the gate enforces it either way.

## The rest of the survey, so nobody repeats it

While the scanner was being validated, pyflakes' *other* categories were read
through on the whole tree. **Nothing else in them is a bug**, which is why the
gate is narrowed to undefined names only:

| Category | Count | Verdict |
|---|---|---|
| unused imports | ~300 | tidiness; many are deliberate re-exports |
| `global X` never assigned in scope | 8 | **not bugs** — every one mutates a dict in place (`_candle_cache[key] = ...`) rather than rebinding, so the `global` is redundant, not wrong |
| f-string missing placeholders | 10 | **not bugs** — stray `f` prefixes on constant strings sitting in lists of otherwise-interpolated ones |
| local assigned but never used | ~12 | dead locals; no behaviour |
| redefinition of unused import | ~12 | function-local re-imports of a module already imported at top |

The `global` category is the one worth remembering: it looks alarming and reads
like "this function meant to update something and doesn't", but in-place
mutation is the actual pattern everywhere it appears.
