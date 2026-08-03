# 010 — Characterize open trade

**Status:** Done (2026-07-20)
**Depends on:** none
**Real-money surface:** places an order via `bridge.place_order` or the EA bridge — tested
against fakes only, never a real/demo account.

## Decision

Same DB approach as prior packs. `self._bridge` replaced by a fake test-double exposing async
`get_fresh_tick()`/`place_order(...)`. `ea_bridge`/`sync.server`/`sync.client` are exercised via
their own natural "unconfigured" defaults (no pairing, no EA instance) for the default-path
tests, and via `ea_bridge.set_instance(fake)` / `db_module.set_app_config("sync_remote_host",
...)` + a patched `sync.client.get_instance` for the two non-default branches.

## Tests first (TDD)

- `tests/core/test_open_trade_characterization.py`:
  - Happy path: places the order via the (fake) Python bridge, inserts the trade row, activates
    the signal, returns `{trade_id, mt5_ticket, entry_price, strategy, managed_by: "python"}`.
  - Raises when trading is paused (`is_trading_paused` true via `trade_pause_until`).
  - Raises when the circuit breaker is active.
  - Raises when `max_open_trades` is already reached.
  - Raises `RuntimeError` when no live tick is available (bridge returns `None`).
  - Raises `RuntimeError` and inserts NO trade row when the bridge rejects the order.
  - EA-managed path: `ea_bridge_enabled=1` + a fake EA instance that's healthy and reports the
    strategy portable — uses the EA's `open_trade` instead of the Python bridge, sets
    `managed_by="ea"`.
  - EA handoff falls through to the Python bridge when the EA instance is `None`, unhealthy, or
    reports the strategy not portable (all three, via the natural "no EA configured" default).
  - `mt5_tp_override` is used verbatim as the broker-side TP instead of derived from
    `STRATEGY_BE_RUNNER`'s TP-selection logic.
  - `STRATEGY_BE_RUNNER` (no override) sends the highest populated TP (tp8 down to tp1) as the
    broker-side TP; every other strategy sends no broker-side TP (`None`) — partial-close is
    managed entirely in-app for those.
  - Remote-forwarding: `sync_remote_host` set (non-empty) + `active_trader` at its default
    (`remote_vps`) + `centralized_signal_gen_enabled=0` raises a "stood down" `ValueError`
    without ever touching the local bridge.
  - Remote-forwarding, centralized mode: same setup with `centralized_signal_gen_enabled=1` and
    a patched `sync.client.get_instance()` returning a fake client whose `send_signal_order`
    returns a success ack — returns the forwarded result (`executed_remotely: True`) without
    ever calling the local bridge.

## What to do

1. Write the test file calling `SimulationEngine.open_trade` via
   `SimulationEngine.__new__(SimulationEngine)` with `_bridge` set to a fake test-double.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order (Python bridge or EA) is ever placed — verified by each fake's own
  call log, not just absence of errors.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset helpers from prior
  packs.

## Notes

15 tests written in `tests/core/test_open_trade_characterization.py`. No `engine.py` bugs
found. One significant environment discovery along the way:

**Missing dependency masked an entire code path.** The two remote-forwarding tests initially
failed with "DID NOT RAISE" / `KeyError: 'executed_remotely'` even though a standalone script
using the same setup raised correctly. Root cause: this repo's actual test venv
(`python -m pytest` resolves to pyenv 3.11.9) was missing `cryptography` — a declared
dependency in `requirements.txt` (`cryptography>=42.0`), present in the *other* Python 3.13
interpreter on this machine but not the one pytest actually uses. `SyncClient.load_config()`
does `from forex_trader.core import secrets as _sec` at the top of the function; `secrets.py`
does `from cryptography.fernet import Fernet, InvalidToken` at module level. Without
`cryptography` installed, that import raises `ModuleNotFoundError` (a subclass of
`ImportError`) — which `open_trade`'s own `except ImportError: pass` (there to make the
Local/Remote sync feature a no-op on installs that haven't configured it) silently swallows.
Net effect: with `cryptography` missing, `open_trade` unconditionally behaves as if no VPS
pairing exists at all, regardless of `sync_remote_host` — not a code bug, but a real gap that
would have silently zero-covered this entire branch (and anything else touching
`secrets.py`/sync config) across the *whole* test suite, not just this pack.

Fixed by installing `cryptography>=42.0` (already a declared, correct requirement) into the
pyenv 3.11.9 venv. All 15 tests pass afterward; repo-wide suite unaffected otherwise (646/648
green, same 2 pre-existing `pytest-asyncio`-missing failures as every prior pack — unrelated,
and now confirmed NOT the same class of issue as the `cryptography` gap, since installing
`cryptography` didn't touch those).

Other findings, all confirming documented behavior with no bugs: the EA handoff correctly
falls through to the Python bridge on any of {no instance, unhealthy, strategy not portable};
`mt5_tp_override` bypasses `STRATEGY_BE_RUNNER`'s highest-populated-TP selection entirely; the
max-open-trades/pause/circuit-breaker gates all fire before the bridge is ever touched (asserted
via the fake bridge's empty call log, not just the raised exception); a bridge-rejected order
inserts no trade row at all.
