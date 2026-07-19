# 040 — MT5 connectivity check

**Status:** not started
**Depends on:** 030-extract-breakout-service-layer.md
**Real-money surface:** no — connectivity/read-only only, no order placement (established
boundary from backend-foundation 050)
**Leverage:** the isolated `MetaTrader 5 DemoValidation` terminal (already set up, left in place)

## Decision

Same connectivity-only validation as backend-foundation 050, reusing the existing isolated
terminal rather than setting up a new one. Confirms real market data (M5/H1/H4 candles,
XAUUSD tick) is reachable — no order placement, per the agent's own policy boundary already
established. This task is lighter than 050 was, since the isolation groundwork already exists.

## What to do

1. Launch the existing isolated terminal if not running.
2. Connect using the same demo credentials (`.local/bridge_credentials.json`).
3. Pull M5/H1/H4 candles and a tick for XAUUSD — confirms the data breakout_signal's generation
   logic actually consumes is reachable in the isolated environment.
4. Report results, close the terminal when done (per Simon's established preference).

## Acceptance

- Isolated terminal connects, pulls real candle data across the timeframes breakout_signal
  actually uses (M5, H1, H4).
- Live app's own terminal confirmed untouched throughout (same `ps aux` check as before).

## Notes

If Simon wants an order round-trip this time, same boundary applies as before: the agent won't
place one. Offer the same manual option (isolated terminal left logged in, Simon places one,
agent records it) if relevant.
