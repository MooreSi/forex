# Core Conservative Trial Handler Migration

Extracts `SimulationEngine._handle_conservative_trial` (core/engine.py) into a
standalone module, following the same characterize (010) -> extract (020) pattern
as every prior `core/engine.py` migration pack (most recently
`core-scalp-runner-handler-migration`).

Conservative Trial strategy (fixed-point levels, six TP tiers):

  TP1  +5 pts  →  5% close (early insurance lock-in)
  TP2 +10 pts  → 30% close; SL moves to entry (breakeven)
  TP3 +14 pts  → 20% close
  TP4 +20 pts  → 40% close; SL steps to TP2 level
  TP5 +27 pts  →  5% close
  TP6 +35 pts  → close all remaining

Unlike the simpler phase-gated handlers (Conservative, Scalp Runner), this
handler can cascade through multiple TP levels within a single tick/call if
price has jumped past more than one level -- but only for TP1/TP3/TP5, which
check `_partial`'s auto-closed return value and only `return` early if the
trade fully closed; TP2/TP4 always `return` unconditionally once their TP
level is reached, regardless of whether the partial close itself succeeded.
This asymmetry is a genuine characterization detail, not a bug, and must be
preserved verbatim during extraction.

See `PROGRESS.md` for task status.
