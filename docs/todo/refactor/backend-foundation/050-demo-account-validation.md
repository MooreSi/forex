# 050 — Demo-account validation

**Status:** Done (2026-07-19) — connectivity-only, accepted by Simon as sufficient
**Depends on:** 040-extract-gd-copy-service-layer.md
**Real-money surface:** yes — needs user sign-off before implementation
**Leverage:** `gd_copy_signal_service.py` (040)

## Problem

010-040 prove the new structure is behavior-equivalent under test, but never against a live
MT5 connection — only against characterization tests with externals mocked. Before this
pattern is trusted for future engines, it needs one real end-to-end run against an actual
(demo) MT5 account.

## Decision

BLOCKED until Simon supplies demo MT5 credentials/config for `forex-refactor2`, kept separate
from the live app's `config.yaml`. Once available, this task connects the new
`gd_copy_signal_service.py` to the demo account (paper/demo order path only) and confirms
signal generation + simulated order handling behave as expected — no live orders, no EA
modification, no UI changes.

**Resolved (2026-07-19):** runs as a standalone script directly importing
`gd_copy_signal_service`/`gd_copy_signal_repo`/`gd_copy_signal_live_execute`, not through the
live app's UI or `ui/app.py`'s startup wiring — task 040 found 7 files still importing the old
`engine.py`/`database.py`, and QUESTIONS.md #7 already ruled UI rewiring out of scope for this
pack. Rewiring the app to actually use the new modules is separate future work.

**Isolation finding (2026-07-19):** `forex_trader/config.py`'s `USER_DATA_DIR` is a hardcoded
constant (no override), the same physical directory the live app uses for its config/DB/
`bridge_credentials.json`. Narrowed scope to a connectivity-only test per Simon's choice
(rather than a full `GDCopyEngine` cycle, which would pull in `core.database`/`core.secrets`
and touch that shared directory).

**MT5 terminal isolation:** the only running MT5 terminal on this Mac was the live app's own
(`terminal64.exe`, PID 91994, running since Jul 7, live-trading). Copied the entire
`MetaTrader 5` install directory (1.4GB) to a second, portable-mode instance
(`MetaTrader 5 DemoValidation`) within the same CrossOver bottle, launched independently via
`MetaTrader5.initialize(path=...)` targeting the new copy specifically — confirmed via `ps aux`
that both terminals ran as separate processes throughout, live one never touched.

**Connectivity: DONE.** Logged into the new demo account (25470480, VantageMarkets-Demo)
through the isolated terminal, confirmed account info and pulled 5 real XAUUSD M15 candles.
One observation for Simon: the reported balance ($651.28) matched what was logged from the
live app's own MT5 connection earlier this session — worth confirming whether this is a new
demo account or the same one already in use elsewhere.

**Order round-trip: not attempted — blocked by design, not a technical blocker.** Placing a demo
order to prove the write path was blocked by the agent's own safety policy (financial trade
execution is off-limits regardless of demo/live status). Simon confirmed the connectivity proof
is sufficient ("happy at this stage it is connecting to mt5") — the isolated terminal
(`MetaTrader 5 DemoValidation`, was PID 88977) has been closed. The copied install directory
(`~/Library/Application Support/CrossOver/Bottles/MetaTrader 5/drive_c/Program Files/
MetaTrader 5 DemoValidation/`, ~1.4GB) was left in place rather than deleted, in case a future
engine's validation task wants the same isolated-terminal pattern again.

## Tests first (TDD)

- `tests/gd_copy_signal/test_demo_integration.py` — an integration test (marked slow/manual,
  not part of the default fast suite) that runs a signal through the real demo MT5 connection
  and asserts it behaves per 020's characterized expectations.

## What to do

1. **STOP** — wait for Simon's explicit sign-off on this task file, plus demo MT5 credentials,
   before writing any implementation code. Only the test skeleton may be drafted ahead of time.
2. Once signed off: wire a demo-only `config.yaml` for `forex-refactor2` (gitignored, never the
   live app's config).
3. Implement `test_demo_integration.py` against the demo account.
4. Run once manually, capture output, report results to Simon — this test depends on an
   external network + broker connection, so it isn't part of routine dev/CI runs.

## Where

- `forex-refactor2/config.yaml` (new, local-only, gitignored, demo credentials)
- `tests/gd_copy_signal/test_demo_integration.py` (new)

## Acceptance

- Explicit sign-off received before any implementation step beyond the test skeleton.
- Demo-only connection confirmed — never touches the live account or the live app's config.
- Signal generation and simulated order handling match 020's characterized expectations.

## Notes

This is the only task in this pack touching anything resembling live trading infrastructure.
Everything else (010-040) is pure code structure, provable entirely through tests without a
market connection.
