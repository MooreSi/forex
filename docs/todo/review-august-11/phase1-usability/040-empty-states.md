# 040 — Real empty states ("do this next")

**Status:** not started · **Touches money:** no · **Layer:** frontend

## Problem

Empty lists say "No signals yet" (or nothing) — dead ends. A newcomer doesn't learn what to do to get
a signal / trade.

## Tests first (TDD)

- `tests/frontend/test_empty_states.py::test_empty_signal_list_shows_next_step` — an empty
  signals/trades view renders a next-step prompt (with a link/action), not a bare "none" — behaviour
  (+ negative control: non-empty view shows data, not the prompt)

## What to do

1. Write the tests; watch them fail.
2. Replace the empty-state text on the Trading / Analysis / signals surfaces with the agreed next-step
   prompts (short next-step wording Darren confirms). Reuse a shared `components/empty_state.py`.
3. `python -m tools.checks all`.

## Where
- `frontend/components/empty_state.py` (new) · the relevant page render functions.

## Acceptance
- Every empty surface tells the user the next action. Green suite.
