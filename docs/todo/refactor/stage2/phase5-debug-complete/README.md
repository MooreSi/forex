# Phase 5 — Debug-mode completion (runs & demos offline)

**Status:** not started
**Gated on:** nothing to start the fakes; the `_make_bridge` seam edit is Simon-gated
**Touches money:** one task — the fake-bridge wiring into `_make_bridge` (Simon sign-off + demo). The
fake itself and all its tests are non-money.

## Goal of this phase

Debug mode actually ticks: a fake MT5 bridge streams synthetic prices and fills orders against an
internal ledger, so Darren can run and demonstrate the whole system end-to-end offline (today the
chart is empty / "MT5 Disconnected"). This **drives the existing local-debug-mode pack**; its config
flag, DB isolation and dashboard login already shipped this session.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-fake-bridge.md](010-fake-bridge.md) | Build FakeMT5Bridge (21-method surface, mapped in the debug pack) + isolation tests; wire the 3-line `_make_bridge` branch (Simon) | YES (wiring only) |
| [020-fakes-and-adapters.md](020-fakes-and-adapters.md) | Fake Telegram reader (scripted signals) + canned news/AI/email so a debug boot makes zero outbound calls | no |
| [030-banner-and-e2e.md](030-banner-and-e2e.md) | Debug banner (unmissable) + a tests/e2e signal→open→manage→close run against the fakes | no |

## Drives / references

[../../infra/local-debug-mode/](../../infra/local-debug-mode/README.md) — tasks 020/030/040/070/080.
The bridge surface is already mapped in its 020 task file.

## Exit criteria

- `FOREX_DEBUG_MODE=1` boots to a serving app with a **moving** fake price and zero outbound
  connections; a bid placed through the runtime lands in the fake ledger and closes cleanly.
- The e2e test drives signal→close offline. Banner shows only in debug.
- `python -m tools.checks all` green; the `_make_bridge` edit demo-signed by Simon before Done.
