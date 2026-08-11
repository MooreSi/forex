# 030 — Debug banner + offline e2e (drives local-debug-mode 070/080)

**Status:** not started · **Depends on:** 010, 020 · **Touches money:** no · **Layer:** frontend + tests
**Drives:** local-debug-mode 070 (banner) + 080 (e2e).

## Problem

Nothing on screen tells you the data is simulated (dangerous once the fake ticks look real), and there
is no end-to-end proof the refactored signal→open→manage→close path actually works.

## What to do

1. Banner: a full-width strip above the header whenever `is_debug()` — "DEBUG MODE — simulated data,
   no real orders". Test: `test_banner_only_in_debug` (+ negative control debug-off).
2. `tests/e2e/test_signal_to_close.py`: boot `backend.src.app.startup()` under debug config; drive a
   scripted signal → parsed → order placed on the fake → fill → tick moves → monitor manages SL/TP →
   close recorded in the debug DB. No real/demo order touched.
3. `python -m tools.checks all`.

## Acceptance
- Banner shows only in debug; the e2e test drives signal→close offline and asserts the close row in
  `forex_trader_debug.db`. Green suite. (This is the proof the refactor is alive — the reason debug
  mode exists.)
