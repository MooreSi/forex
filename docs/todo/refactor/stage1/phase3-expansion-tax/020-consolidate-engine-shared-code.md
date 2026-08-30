# 020 — One home for shared engine code; break the import cycles

**Status:** not started
**Depends on:** 010-delete-dead-code.md (consolidate the living, not the dead)
**Touches money:** no (signal *computation* moves verbatim; order paths untouched)
**Layer:** service
**Leverage:** `/split-file`'s verbatim-move discipline; the structure gates enforce the result

## Problem

Shared engine mathematics has no home (review backend #10): `breakout_signal` imports its ten core
indicators from sibling `test_signal` (`signal_generator.py:22-33`) — a *production* engine
depending on a *test* engine's package; level detection exists three times (drifted?); and the
cross-service graph has real cycles: risk↔cluster (8/8), trading↔broker, positions↔trading. Cycles
mean nothing can be reasoned about, or split, in isolation — this is the single biggest structural
tax on expansion.

## Decision

Create `services/signals/indicators/` (or extend `signals/` — it is the natural shared-signal
home) and move the ten indicators + one blessed level-detection implementation there, verbatim.
Engines import from the shared home; `test_signal` becomes a consumer like the others. Break each
named cycle by extracting the interface the "lower" side actually needs (e.g. trading depends on a
broker *protocol*, broker stops importing trading). Add the no-cycle rule to the structure gates so
it ratchets.

## What must NOT change

- Indicator outputs: byte-identical — characterization tests on fixture candles pin every moved
  indicator before the move.
- Which level-detection implementation is "blessed" per engine: if the three copies have diverged,
  each engine keeps **its own current numbers** until the owner explicitly chooses a survivor —
  unification of *behaviour* is a separate, owner-signed decision; this task unifies *location*.
- The four layer contracts stay at zero.

## Tests first (TDD)

- `tests/signals/test_indicator_characterization.py::test_<indicator>_pinned` ×10 — fixture
  candles → captured outputs, before the move; must pass unmodified after — characterization
- `::test_characterization_can_fail` — perturb one input, capture differs — control
- `tests/refactor/test_engine_imports.py::test_no_cross_engine_internal_imports` — no engine
  imports another engine's modules — structural
- `::test_no_cycles_between_named_services` — risk↔cluster, trading↔broker, positions↔trading at
  zero — structural (this is the new gate rule)
- Negative control: planted cross-import fails the gate — control

## What to do

1. Write the characterization tests against the *current* import locations; green first (they pin,
   not fail — the failure to watch is the structural tests against today's tree).
2. Move indicators verbatim to the shared home; flip engine imports; run characterizations.
3. Level detection: diff the three copies; report divergence to the owner; relocate all three
   beside each other under the shared home with engine-named entry points until a survivor is
   chosen.
4. Break the three cycles one pair per commit (interface extraction, dependency pointing down).
5. Add the cycle rule to the structure gate; `python -m tools.checks all`.

## Where

- `backend/src/services/signals/` — the shared home
- `backend/src/services/{breakout_signal,reversal_engine,test_signal}/` — import flips
- `backend/src/services/{risk,cluster,trading,broker,positions}/` — cycle breaks
- `tools/` structure gate — new rule

## Acceptance

- Grep: zero cross-engine internal imports; cycle gate green with negative control demonstrated;
  all ten characterizations unmodified-green.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- The level-detection divergence finding may turn out to be a real trading-behaviour question —
  if the three copies produce different levels today, the owner needs to see that diff regardless
  of this refactor.

---

## Correction to this task's premise, 2026-08-30

The task says *"`breakout_signal` imports its ten core indicators from sibling
`test_signal` — a **production** engine depending on a **test** engine's
package"*.

**`test_signal` is not a test engine.** It is the **Bounce engine**, and the
package is simply misnamed. `controllers/engines_controller.py` imports it as
`bounce`, and `breakout_signal/signal_generator.py`'s own comment above the
import says *"Re-export shared utilities from the bounce engine"*.

So the dependency is production→production. That is still untidy — shared
indicators living inside one engine's package rather than a shared home — but
it is **not** the layering violation the review described, and the urgency
should be read down accordingly.

### The naming had a real cost, now fixed

pytest collects any module-level name matching `Test*` as a test class. Two
test files imported `TestSignalEngine` (production code) directly, so pytest
tried to collect it on every run and emitted a `PytestCollectionWarning` each
time. It was saved from actually being instantiated and run **only** because
the class happens to have an `__init__`.

That is a latent hazard, not just noise: a `Test*`-prefixed production class
without an `__init__`, imported into any test module, would be instantiated and
"run" by pytest.

Fixed at the import — both files now use `TestSignalEngine as BounceEngine`,
which removes the warning and the hazard, and reads truthfully. Restricting
`python_classes` in `pyproject.toml` was the obvious alternative and is the
wrong one: it would silently stop collecting the suite's own `TestX` classes,
which is a far worse failure than a warning.

### Still open

- The shared indicators still live in the Bounce engine's package. Moving them
  to a shared home is a pure move, behaviour-neutral, and worth doing — but it
  fixes no bug.
- Renaming `test_signal` to `bounce` would remove the confusion at its source.
  That is a wide rename touching imports across the app, and it deserves its
  own change rather than riding along with anything else.
- "Level detection exists three times (drifted?)" is **unverified**. If those
  three have drifted, consolidating them changes signal generation on live
  engines — that is a money-path change needing a demo, not a tidy-up. Check
  whether they are identical before treating it as a refactor.
