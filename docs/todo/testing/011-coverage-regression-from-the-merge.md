# 011 — The coverage ratchet is failing, and it is the merge's

**Status:** measured, not fixed
**Blocks:** `python -m tools.checks all` going green
**Touches money:** yes, indirectly — two of the three areas are the money path

## What the ratchet says

```
CRITICAL backend/src/runtime.py:            63.9% < floor 72.2%  (206 statements uncovered)
CRITICAL backend/src/services/positions:    75.8% < floor 86.3%  (1119 statements uncovered)
CRITICAL backend/src/services/trading:      86.4% < floor 88.0%  (286 statements uncovered)
```

Measured by `python -m tools.checks all` on a full run, 2026-08-26.

## Where it came from

The floors were set before the 2026-08-25 upstream merge. That merge landed in exactly
these three areas:

| area | merge added |
|---|---|
| `backend/src/runtime.py` | 293 insertions |
| `backend/src/services/positions` | 6,341 insertions across 27 files |
| `backend/src/services/trading` | 1,326 insertions across 12 files |

Roughly 7,960 lines of upstream code arrived without enough tests to hold the percentage,
so the floors — which are a record of what was once covered — are now above reality.

This branch's own contribution is 19 lines, all in `runtime.py`, of which **one** was
uncovered: the `close_cmd` delegate. That is now tested
(`tests/core/test_runtime_facade.py`), so the branch contributes nothing to the shortfall.

## Why the floors must not be lowered

`tools/…/coverage_gate` says it directly: *"Do not lower the baseline to pass — the floor
is the record of what was once covered."* Lowering them would erase the fact that this code
was better covered before the merge, and these are the position-management and trading
services — the parts that place, size and close real orders.

## What to do

Write tests for what the merge brought in, area by area, largest gap first:

1. **`services/positions`** — the biggest gap by far (1,119 statements). 27 files changed;
   start by listing which of them are new and which are untested.
2. **`runtime.py`** — 206 statements. Note this file is at its design floor and exempt from
   splitting, so the work is tests, not restructuring.
3. **`services/trading`** — 286 statements, and the closest to its floor.

Then re-run `python -m tools.checks all` and confirm each area is back above its floor.

## A correction worth keeping

During this session I found a `.coverage.json` in the working tree, saw 53% overall, and
concluded it was "provably a partial run" and deleted it. It was not — a proper full run
produced the same three failures with identical percentages. 53% overall is simply what
this codebase measures. I dismissed a real regression signal on a bad inference; the lesson
is to re-measure rather than reason about why a number looks wrong.
