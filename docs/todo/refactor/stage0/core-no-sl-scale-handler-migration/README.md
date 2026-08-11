# Core No-SL-Scale (Trend Ratchet) Handler Migration

Extracts `SimulationEngine._handle_no_sl_scale` (core/engine.py) into a standalone
module, following the same characterize (010) -> extract (020) pattern as every
prior `core/engine.py` migration pack. This is the last of the four TP/SL strategy
handlers named in the standing "continue with all of them" instruction (after
`core-handle-orb-fixed`/`core-handle-scale-out`/`core-handle-be-runner`/
`core-tp-ladder-handlers`/`core-handle-trail-stop`/`core-handle-protected-scale`/
`core-conservative-handler`/`core-scalp-runner-handler`/`core-conservative-trial-handler`).

Trend Ratchet strategy (formerly No-SL Scale Out), up to 8 dynamic TP tiers:

  Emergency SL at 1.5x signal SL distance (set at trade open; ADX>30 required at entry)
  TP1              -> 20% partial close
  TP2              -> skip (mark for UI)
  TP3              -> 20% partial close + SL -> TP1 level
  TP4              -> SL -> TP2 level (skip, mark for UI)
  TP5              -> SL -> TP3 level (skip, mark for UI)
  TP6              -> SL -> TP4 level (skip, mark for UI)
  TP7              -> SL -> TP5 level (skip, mark for UI)
  TP8 (or last TP) -> close all remaining lots

The number of active tiers is dynamic (`last_tp_num`, derived from which `tp1..tp8`
columns are actually set on the trade), and the handler can cascade through
multiple TP checks within a single call when price gaps past more than one level.

See `PROGRESS.md` for task status.
