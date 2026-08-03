# 040 — MT5 connectivity check

**Status:** Done (2026-07-20)

Reused the isolated `MetaTrader 5 DemoValidation` terminal, confirmed real tick + H1/M15/H4/M5
candle data (120/60/40/30 bars respectively, matching what `_run_cycle` actually requests).
Live terminal (PID 91994, unbroken since 2026-07-07) confirmed untouched via `ps aux` before
and after. Isolated terminal closed after the check.
**Depends on:** 030
**Real-money surface:** no — connectivity/read-only only

## Decision

Same as the other two packs: reuse the isolated `MetaTrader 5 DemoValidation` terminal, pull
the timeframes test_signal's generation logic consumes (H1/M15/H4/M5), confirm the live
terminal stays untouched, close the isolated one after.
