# 020 — FakeMT5Bridge + the `_make_bridge` seam

**Status:** not started
**Depends on:** 010-debug-config.md
**Touches money:** YES — run `/safe-change` first. Not Done without owner sign-off + a demo
session. (The fake itself is new code; the money part is the edit to `_make_bridge` in
`runtime.py:170-179` and the bridge-subprocess/EA-bridge skips.)
**Layer:** service (broker) + composition root
**Leverage:** the 19-method surface in REVIEW.md §1; `sim_account.py` balance conventions;
`tests/conftest.py:103 make_engine`; the 12+ `_FakeBridge` test classes to consolidate

## Problem

Every price, candle, account read and order action goes through `self._bridge`
(`runtime.py:187`), which can only be a live HTTP or native MT5 connection. Without MT5
credentials nothing above the bridge can execute — engines, monitor loops, trading paths, the
frontend ticker are all untestable.

## Decision

New `backend/src/services/broker/fake_bridge.py` — `FakeMT5Bridge` implementing the exact
duck-typed surface (all 19 methods + `url`/`is_configured`), with:

- a tick source: seeded random-walk XAUUSD by default, or a scripted JSON scenario
  (QUESTIONS.md #2) with deterministic timestamps;
- candles aggregated from the same tick history (so tick and candle views agree);
- an internal ledger: account (balance/equity/margin), open positions with tickets, deal
  history; `place_order`/`close_position`/`partial_close`/`modify_order` mutate it with exact
  fills (QUESTIONS.md #4) and return the same success/`{"error": ...}` dict shapes as
  `mt5_bridge.py`;
- an error-injection hook (`inject_error(method, response, count)`) so tests can exercise the
  rejection paths the 2026-08-08 review flagged (C1/C2) — never raising where the real client
  wouldn't.

Wire as a third branch in `_make_bridge(config)`: debug on → `FakeMT5Bridge()`. In `run.py`,
debug skips `_start_mt5_bridge()`; the EA bridge stays off (it is already risk-setting gated —
assert, don't re-gate).

## What must NOT change

- `_make_bridge` with debug off: same two branches, same order, same defaults.
- No edits to `mt5_client.py`, `mt5_native.py`, `mt5_bridge.py`, or anything in
  `services/trading` / `services/positions` / `services/risk`.
- Runtime shape guards pass unmodified: `tests/core/test_runtime_facade.py`,
  `test_runtime_dissolution_shape.py`, `test_runtime_supervisor_shape.py`.
- Return conventions: the fake **never raises** where the real clients return
  `None`/`[]`/`{"error"}`.

## Tests first (TDD)

- `tests/core/test_fake_bridge_surface.py::test_surface_matches_real_clients` — introspect
  `MT5BridgeClient` + `NativeMT5Bridge` public async/sync methods and assert `FakeMT5Bridge`
  matches names + signatures — structural. Negative control:
  `::test_surface_check_can_fail` (patch a method away, assert the checker reports it).
- `tests/core/test_fake_bridge_ticks.py::test_scripted_scenario_is_deterministic` — same
  scenario twice → identical tick/candle series — behaviour
- `::test_candles_agree_with_ticks` — candle OHLC derivable from the tick script — behaviour
- `tests/core/test_fake_bridge_orders.py::test_order_lifecycle` — place → in `get_positions`,
  balance/margin move; close → gone, deal in `get_deal_history` — behaviour
- `::test_partial_close_and_modify` — lots reduce; SL/TP update visible — behaviour
- `::test_error_injection_returns_error_dict_and_no_state_change` + negative control (without
  injection the same call succeeds) — boundary
- `tests/core/test_make_bridge_debug.py::test_debug_off_selects_same_classes_as_today` —
  regression — and `::test_debug_on_selects_fake` — wiring

## What to do

1. **`/safe-change` first** (this file is the paper trail; record the checklist outcome in
   PROGRESS.md).
2. Write the tests; watch them fail.
3. Implement `fake_bridge.py` (mind the 800-line gate — split tick-source / ledger into
   siblings under `services/broker/` if needed, e.g. `fake_market.py`).
4. Edit `_make_bridge` (three-line branch) + `run.py` subprocess skip.
5. Migrate `tests/conftest.py make_engine` docs/fixtures to offer the shared fake; leave the
   existing per-file `_FakeBridge` classes in place (consolidating 12 test files is follow-up,
   not this task — note in PROGRESS if attempted).
6. `python -m tools.checks all`.

## Where

- `backend/src/services/broker/fake_bridge.py` (+ siblings) — new
- `backend/src/runtime.py:170-179` — the branch (MONEY)
- `run.py:66-125 / :222` — subprocess skip in debug
- `tools/debug_scenarios/` — first scenario file(s)

## Acceptance

- With `FOREX_DEBUG_MODE=1` and an empty config, `python run.py --no-browser` boots to a
  serving app with a moving fake price and zero outbound connections (verify with no network —
  e.g. disable the adapter or watch netstat).
- **The killer test:** `test_order_lifecycle` — a bid placed through the runtime facade lands in
  the fake ledger and closes cleanly.
- `python -m tools.checks all` green, output pasted into PROGRESS.md; owner sign-off + demo
  session recorded before Done.

## Notes

The fake must be able to *misbehave on demand* — the unchecked-`modify_order` class of bug
(backend review C1) is only testable if the fake can return `{"error": ...}` mid-scenario. Keep
injected errors scenario-scriptable, not just programmatic.
