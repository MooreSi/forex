# SPEC — Local debug mode: run the whole system offline on fakes

**Status:** Draft
**Owner:** Darren (final sign-off: Simon — he holds the live account and all API keys)
**Touches money:** yes — one task edits the bridge-selection seam in `runtime.py`; nothing else
touches order code. Sign-off + demo session required for that seam before it ships to the live
machine.
**Created:** 2026-08-10

---

## Problem

The refactored system has never been run by the person refactoring it. All credentials — MT5
account, Telegram API/bot, Anthropic key, licence — live with Simon; Darren has none and cannot
boot the app, let alone watch a signal become a bid and a close. Today the app hard-depends on:

1. A live MT5 terminal via `mt5_bridge.py` (HTTP on macOS/Wine, in-process native on Windows) —
   every tick, candle, account read, and every place/close/modify.
2. Telegram: a Telethon user session for inbound signals, a bot token for alerts/commands.
3. A licence key checked by `config/licence/guard.py:enforce()` before anything else starts
   (`run.py:219`).
4. Outbound calls: news calendar (ForexFactory/Finnhub), AI (Anthropic/DeepSeek), email
   (Resend/Mailjet/SMTP), cluster/fleet admin at a hardcoded IP.

There is no interface for any of these — the broker "interface" is duck typing between two
classes selected in `runtime.py:170 _make_bridge()`. There is also **no login**: the dashboard on
port 8888 is open to anyone who can reach it (`frontend/app.py:456` admits this in its own help
text).

## Goal

After this ships, `FOREX_DEBUG_MODE=1` (or `debug_mode: true` in config.yaml) boots the complete
app — backend, engines, monitor loops, frontend — with **zero network access and zero
credentials**: a fake MT5 bridge streams synthetic ticks/candles and fills orders against an
internal ledger, a fake Telegram reader feeds scripted signal messages through the real parser,
news/AI/email return canned data, and the licence check passes on a locally generated (real,
verified) key. The frontend shows an unmissable banner whenever debug mode is on. The dashboard
gains a real username/password login in **both** modes. A `tests/e2e/` suite drives the full
signal → parse → place → manage → close path against the fakes, so the refactor can be proven
working before Simon ever runs it.

The adapters are written as named, documented seams — not test hacks — so future real
integrations (another broker, another signal source) plug into the same ports.

## Non-goals

- No change to any strategy, sizing, SL/TP, or risk logic. The fakes sit *below* the existing
  duck-typed bridge surface; everything above it runs unmodified.
- No reshaping of the frozen close path — the fakes receive its calls; they do not change it.
- No new retry/reconciliation logic (that is SPEC-002/003).
- No multi-user auth, roles, or remote access hardening beyond a single username/password.
- No backtesting engine — the fake stream is for *liveness* testing, not strategy evaluation.
- No licence-system changes: no bypass flag, no guard edit. Debug mode uses a genuinely valid
  key generated with the existing `keygen.py` (see Open questions — needs Simon's sign-off).

## What must NOT change

- **The frozen close path** (`close_trade`, `record_close`, `_make_close_trade_ctx`,
  `partial_close_trade`) — byte-identical.
- **`_make_bridge` behaviour when debug mode is off**: same two branches, same defaults, same
  config keys. The debug branch is strictly additive and the existing
  `tests/core/test_runtime_*` shape guards pass unmodified.
- **`guard.enforce()` is not edited.** Debug mode must pass it with a valid key, not around it —
  per the "no licence or auth bypass" golden rule.
- **Default config**: `debug_mode` defaults to **false/absent**; a config.yaml with no new keys
  behaves exactly as today. Live/demo `account_env` DB files are never opened in debug mode
  (debug gets its own DB file).
- All existing tests pass unmodified; the four import contracts stay at zero; no ratchet
  baseline rises.
- The 19-method bridge surface (get_tick … get_tick_at) — the fake implements it, it does not
  alter it.

Affected money surface (sign-off + demo session required): `backend/src/runtime.py:170-179
_make_bridge()` and the `run.py` bridge-subprocess skip. Nothing else in `services/trading`,
`services/risk`, or `services/positions` is edited.

## Design

Full breakdown and task files: [README.md](README.md) (this pack).
Shape in one paragraph per seam:

- **Config** (`backend/src/config/__init__.py`): new `debug_mode` key via the existing `_e()`
  env-over-yaml pattern (`FOREX_DEBUG_MODE`), plus `is_debug()` helper. Debug forces
  `account_env`-independent DB isolation (`forex_trader_debug.db`).
- **Broker port** (`backend/src/services/broker/fake_bridge.py`, new): `FakeMT5Bridge`
  implementing the exact duck-typed surface of `MT5BridgeClient`/`NativeMT5Bridge` — synthetic
  XAUUSD tick stream (deterministic scripted scenarios + random-walk default), candles derived
  from the same stream, internal account/positions ledger, place/close/partial/modify with
  realistic fills and the same `{"error": ...}` return conventions. Selected as a third branch
  in `_make_bridge()`; `run.py` skips the bridge subprocess and the EA bridge stays off.
- **Signals port** (`backend/src/services/telegram/fake_reader.py`, new): same buffer contract
  as `TelegramReader`; replays scripted signal messages (the real Telegram message shapes) into
  the existing `scan_messages`/parser path. Outbound `alerts.send_message` and the bot loop
  no-op in debug.
- **News / AI / email**: canned responses behind the existing call sites
  (`utils/news_calendar.py`, `test_signal/news_filter.py`, `services/ai/provider.py`,
  `services/notifications/email_service.py`).
- **Licence**: `tools/generate_debug_licence.py` writes a valid, expiring key for this machine
  using the existing `keygen.generate_licence_key`; `enforce()` runs untouched.
- **Login** (both modes): NiceGUI `storage_secret` + auth middleware on the dashboard page,
  scrypt-hashed password reusing `services/cluster/remote/auth.py`'s helpers, a
  `tools/set_dashboard_password.py` setter, login/logout pages.
- **Banner**: full-width strip above the header row (`frontend/app.py:893`) whenever
  `is_debug()` — "DEBUG MODE — simulated data, no real orders".
- **E2E** (`tests/e2e/`): boots `backend.src.app.startup()` under debug config and asserts the
  full path: scripted signal → parsed → order placed on the fake → fill → tick moves → monitor
  manages SL/TP → close recorded in the debug DB.

## Test plan

Per-task detail lives in the pack task files; the contract at spec level:

| Behaviour | Test | Type |
|---|---|---|
| `debug_mode` defaults off; absent key = today's behaviour | `test_config_debug_mode_defaults_false` | regression |
| `_make_bridge` returns the same classes as today when debug off | `test_make_bridge_unchanged_when_debug_off` | regression |
| Debug on → `FakeMT5Bridge`, no subprocess, EA bridge off | `test_make_bridge_selects_fake_in_debug` | wiring |
| Fake implements every bridge method with matching signatures | `test_fake_bridge_surface_matches_real` (introspection) | structural |
| Fake fills: place → position appears; close → history + balance move | `test_fake_bridge_order_lifecycle` | behaviour |
| Fake honours `{"error"}` convention incl. injectable rejections | `test_fake_bridge_error_injection` + negative control | boundary |
| Scripted signal reaches the parser and yields a parsed signal row | `test_fake_reader_feeds_scan_messages` | wiring |
| Debug DB file is `forex_trader_debug.db`, never the demo/live file | `test_debug_db_isolation` | boundary |
| Login required in both modes; wrong password rejected | `test_dashboard_requires_login` / `..._rejects_bad_password` | behaviour |
| Banner rendered only when debug on | `test_banner_only_in_debug` + negative control | wiring |
| Full e2e: signal → open → manage → close, offline | `tests/e2e/test_signal_to_close.py` | e2e |

Negative controls throughout: every "X does not happen" assertion is paired with a case proving
the detector fires (e.g. the surface-match test must fail when a method is deleted from the fake).

## Rollout

- Behind `debug_mode` (default off). Simon's machine sees zero behaviour change until the login
  task ships — that one is deliberate and user-visible (first-run password setup).
- Revert: remove the config key; the debug branch is dead code with the flag off.
- The `_make_bridge` seam change needs a demo session on Simon's side before live use.

## Open questions

Tracked with recommendations in [QUESTIONS.md](QUESTIONS.md).
Headlines: (1) Simon must sign off the locally-generated debug licence key approach — the golden
rules ban bypasses, this uses the real verifier, but it is his call; (2) scripted-scenario format
for the fake stream; (3) first-run password setup flow; (4) whether fake fills model slippage.

## Verification

Filled in when shipped:

- [ ] full suite green
- [ ] all four gates green
- [ ] app boots and serves **offline with `FOREX_DEBUG_MODE=1` and no config credentials**
- [ ] e2e signal→close run recorded in the debug DB
- [ ] login required on the dashboard in both modes
- [ ] no real or demo order touched by this work or its tests
