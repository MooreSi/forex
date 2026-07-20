# 040 — MT5 connectivity check

**Status:** not started
**Depends on:** 030
**Real-money surface:** no — connectivity/read-only only

## Decision

Same as the other two packs: reuse the isolated `MetaTrader 5 DemoValidation` terminal, pull
the timeframes test_signal's generation logic consumes (H1/M15/H4/M5), confirm the live
terminal stays untouched, close the isolated one after.
