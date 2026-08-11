# 010 — Engine panels → `engines_controller`

**Status:** not started
**Depends on:** none — can start immediately
**Touches money:** no. The engines *generate* signals; they do not place orders. Starting or stopping an engine changes whether signals arrive, not whether a position opens — that gate is `SimulationEngine.open_trade()` and this task does not touch it.
**Layer:** frontend → controller
**Leverage:** `backend/src/controllers/engines_controller.py` already exists and already owns this domain

## Problem

The three engine panels and the app shell import engine service singletons directly:

| File | Line | Import |
|---|---|---|
| `frontend/app.py` | 982–984 | `breakout_signal_service`, `test_signal_service`, `reversal_engine_service` (function-local, inside `_mode_sub_engines()`) |
| `frontend/pages/remote_node.py` | 22–24 | the same three |
| `frontend/pages/breakout_panel.py` | 16 | `breakout_signal_service as bo_engine_module` |
| `frontend/pages/reversal_panel.py` | 25 | `reversal_engine_service as re_engine_module` |
| `frontend/pages/test_panel.py` | 19 | `test_signal_service as test_engine_module` |

`engines_controller.py` exists and re-exports each engine's `panel_data` module — but not the
service singletons themselves, so anything needing `get_instance()`, `start()`, `stop()` or
`is_running` reaches around it. That is the whole gap.

Note the shape of the calls in `app.py:1032-1035` and the mode toggle: they iterate over the three
engines and call `start()` on any that isn't running. The controller needs to name that operation,
not expose the singletons for the page to loop over — otherwise this repeats
`engines_controller`'s own documented mistake of letting the page choose.

## Decision

Add named lifecycle functions to `engines_controller` — `get_status()`, `start_all()`,
`stop_all()`, and per-engine equivalents keyed by name — and route all five files through them.
Do **not** re-export the singletons; that would satisfy the contract while leaving the page in
charge, which is the failure the controller's docstring already describes.

The alternative — one controller per engine — was rejected: the three panels are near-identical and
the app shell always operates on all three at once.

## What must NOT change

- The three engines' start/stop semantics and ordering, exactly as `app.py:1032-1035` and
  `app.py:1050-1075` perform them today, including the "only start if not already running" guard.
- The function-local import at `app.py:982` **stays function-local**. It is inside
  `_mode_sub_engines()` to defer engine imports past app boot; hoisting it to module level changes
  startup ordering.
- `remote_node.py`'s stand-down / take-over handshake behaviour.
- Existing tests in `tests/breakout_signal/`, `tests/reversal_engine/`, `tests/test_signal/` pass
  unmodified except for mock-target relocations.

## Tests first (TDD)

Per [docs/system/rules/40-testing.md](../../../../../system/rules/40-testing.md): write these, run them, watch them fail,
confirm the failure is the one you expected.

- `tests/controllers/test_engines_controller_lifecycle.py::test_start_all_starts_only_stopped_engines`
  — surface. Fakes for the three services; asserts `start()` called on the stopped one and not on the
  running one.
- `tests/controllers/test_engines_controller_lifecycle.py::test_the_fake_records_a_start_it_should_not_have_had`
  — **negative control**. Proves the fake can actually detect a spurious `start()`; without it the
  assertion above is unfalsifiable.
- `tests/controllers/test_engines_controller_is_flat.py::test_lifecycle_functions_forward_without_logic`
  — structural. AST-asserts each new function body is a call/return, no loops or conditionals beyond
  the documented guard.
- `tests/frontend/test_engine_panels_wiring.py::test_panels_reach_engines_through_the_controller`
  — wiring, one case per panel. Patches the controller function and asserts the panel's handler hits
  it.
- `tests/frontend/test_engine_panels_wiring.py::test_wiring_check_detects_a_direct_service_import`
  — **negative control** for the wiring assertion.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Add the lifecycle functions to `engines_controller.py`, forwarding to each engine service. Extend
   `__all__`.
3. Rewire `breakout_panel.py`, `reversal_panel.py`, `test_panel.py` — one file per commit so a
   regression bisects cleanly.
4. Rewire `remote_node.py:22-24`.
5. Rewire `app.py:982-984`, keeping the import function-local.
6. `python -m tools.refactor_audit.import_contracts --check` — confirm the count dropped; record the
   new number in PROGRESS.md.
7. `python -m tools.checks all`.

## Where

- `backend/src/controllers/engines_controller.py` — gains named lifecycle functions
- `frontend/pages/breakout_panel.py`, `reversal_panel.py`, `test_panel.py`, `remote_node.py` — imports rewired
- `frontend/app.py:982-984` — rewired, still function-local

## Acceptance

- All five files import from `backend.src.controllers` only.
- The contract count has dropped by the number this task owns; the new figure is in PROGRESS.md.
- **The killer test:** start each engine from its panel, stop it, and toggle Local→Remote→Local with
  the mode button — all three engines stop and restart exactly as before, with no direct service
  import anywhere in the path.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- `engines_controller` currently imports `panel_data` modules and `services/risk/settings`. Adding
  service singletons keeps it inside `controllers-never-import-repos` as long as it never reaches a
  `*_repo` module — check the gate after, not just at the end of the phase.
- The three panels being near-identical is real duplication, and collapsing them into one
  parameterised component is explicitly **out of scope** for this pack (see the README). Note what
  you observe; don't act on it here.
