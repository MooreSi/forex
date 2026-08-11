# 010 — Fake MT5 bridge (drives local-debug-mode 020)

**Status:** not started · **Touches money:** YES — only the `_make_bridge` seam edit (Simon sign-off + demo). The fake + its tests are non-money.
**Drives:** [../../infra/local-debug-mode/020-fake-mt5-bridge.md](../../infra/local-debug-mode/020-fake-mt5-bridge.md) — the 21-method surface is already mapped there.

## Problem

In debug mode the chart is empty / "MT5 Disconnected": `_make_bridge` returns a real bridge that can't
connect without MT5, so nothing ticks. Darren can't see or demo the system working.

## What to do

1. **Non-money, do now:** build `backend/src/services/broker/fake_bridge.py` (`FakeMT5Bridge`) per the
   mapped surface — deterministic synthetic XAUUSD stream (closed-form `mid(step)` so `get_tick_at`
   works; split tick engine into `fake_market.py` to stay under 800 lines), an internal
   ledger, place/close/partial/modify with the real `{"error": ...}` conventions, and an
   error-injection hook. Its isolation tests (surface-match with negative control, tick determinism,
   order lifecycle, error injection) are all non-money.
   IMPORTANT: trace `open_trade.py`/`monitor_loop.py`/`sim_account.py` for the exact dict shapes the
   CONSUMERS read before finalising `place_order`/`get_positions` returns.
2. **Money, Simon-gated:** `/safe-change`, then the 3-line debug branch in `runtime.py:_make_bridge`
   (debug → FakeMT5Bridge) + the `run.py` bridge-subprocess skip. Regression test:
   `test_make_bridge_unchanged_when_debug_off`. Sign-off + demo before Done.
3. `python -m tools.checks all`.

## Acceptance
- `FOREX_DEBUG_MODE=1` shows a **moving** price and an empty→filled position through the fake ledger;
  debug-off `_make_bridge` byte-identical. Green suite; seam demo-signed by Simon.
