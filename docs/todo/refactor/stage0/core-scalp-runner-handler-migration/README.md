# Core Scalp Runner Handler Migration

Extracts `SimulationEngine._handle_scalp_runner` (core/engine.py) into a standalone
module, following the same characterize (010) -> extract (020) pattern as every
prior `core/engine.py` migration pack (most recently
`core-conservative-handler-migration`).

Scalp Runner strategy (fixed-point levels, three phases):

  SL   = fill ∓ 10 pts
  TP1  = fill ± 3 pts  →  close 50% of position (SL untouched)
  TP2  = fill ± 4 pts  →  move SL to entry (breakeven); trailing starts
  After TP2: trail remaining 50% with a fixed 3-pt stop, floored at breakeven.

See `PROGRESS.md` for task status.
