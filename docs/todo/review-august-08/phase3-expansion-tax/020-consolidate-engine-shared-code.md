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
