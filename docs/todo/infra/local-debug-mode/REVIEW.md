# Local debug mode — evidence: the current external-dependency surface

Read-only code survey, 2026-08-10 (AST/grep over the working tree; nothing executed, no DB
writes, no MT5). This is the map every task in the pack builds on. Line numbers are as of today.

## 1. MT5 / broker — the seam and the surface to fake

Two interchangeable implementations, duck-typed, no ABC/Protocol:

- HTTP (macOS/Wine): `backend/src/services/broker/mt5_client.py:55 MT5BridgeClient(bridge_url)`
  → `mt5_bridge.py` (repo root) over httpx.
- Native in-process (Windows): `backend/src/services/broker/mt5_native.py:50 NativeMT5Bridge` —
  exec-loads `mt5_bridge.py` as a module, calls its privates on a thread.

**Selection point (the injection seam): `backend/src/runtime.py:170-179 _make_bridge(config)`**,
assigned to `self._bridge` at `:187`.

The full method surface the fake must implement (both classes, identical set):
`startup/shutdown`, `url`, `is_configured`, `get_tick` (1s cache), `get_fresh_tick`,
`get_candles(timeframe,count)` (5s cache), `get_candles_for_symbol`, `get_candles_range`,
`get_health`, `get_account`, `get_positions`, `place_order(direction,lots,sl,tp,comment)`,
`close_position(ticket)`, `partial_close(ticket,lots)`, `modify_order(ticket,sl,tp)`,
`send_credentials`, `reconnect`, `enable_autotrading`, `get_deal_history(days)`,
`get_position_history(ticket)`, `get_tick_at(ts)` — `mt5_client.py:61-404` /
`mt5_native.py:59-338`. Return conventions: `None` / `[]` / `{"error": ...}` on failure —
**never raises**. The fake must mirror this exactly (the 2026-08-08 backend review's C1/C2 hang
on those `{"error"}` dicts being unchecked; the fakes must be able to produce them).

Bridge config: `config/__init__.py:92-106` (`mt5_bridge_url` default `http://localhost:9010`,
`mt5_bridge_enabled`, `mt5_native_bridge_enabled`, `ea_bridge_port` 9111). Bridge subprocess:
`run.py:66-125 _start_mt5_bridge()` (skipped on win32 native). Third broker channel: **EA TCP
bridge** `services/broker/ea_bridge.py:63` (newline-JSON to the MQL5 EA, started
`runtime.py:303-309`, gated by risk setting `ea_bridge_enabled`, `db/database.py:798`) — in
debug it stays disabled, not faked.

Market data consumers — all poll `self._bridge`, no external market API anywhere:
test_signal `test_signal_service.py:205,248`; breakout `breakout_signal_service.py:186,213-216`
(M5/H1/H4); reversal `reversal_engine_service.py:186,235-247` (H1/M15/H4). Engines receive the
bridge at `backend/src/app.py:176,181,196`. Other consumers: positions monitor
(`monitor_cycle.py`/`monitor_loop.py`), `position_sync.py`, `watchdog.py:101`,
`services/trading/*`, `frontend/app.py:1395` (send_credentials).

Existing sim/fake state: **no** sim/dry-run flag exists. `services/trading/sim_account.py` is a
paper *balance* ledger (not a bridge fake). DB swap precedent: `db/connection.py:62 set_db()`.
Kill-switch precedent: `runtime.py:276 set_bridge_inhibit_reconnect`.

## 2. Telegram

- Inbound (Telethon user session): `services/telegram/reader.py:40 TelegramReader(config)`;
  client at `reader.py:125-133`; started `app.py:171,207`; messages buffer via
  `reader_listener.py:229 _buffer_message` → `runtime.py:863 _signal_scanner_loop` →
  `services/signals/scan_messages.py:88` → `services/signals/parser.py` (`parse_gold_signal:333`,
  `parse_gd2_signal:408`, `parse_instant_entry:271`, `parse_limit_order_signal:588`,
  `validate_signal:607`). Config: `telegram_api_id/hash/phone/2fa/session/signal_group_id`
  (`config/__init__.py:150-155`).
- Outbound bot HTTP: `services/telegram/alerts.py:150 send_message` → api.telegram.org (`:161`);
  command long-poll `bot_loop.py:50,107`. Token read from DB
  (`db_module.get_telegram_config()`, `alerts.py:157-160`).

## 3. News calendar

`utils/news_calendar.py` — MT5 source `:100-119`; Finnhub `:124-164` (urllib `:140`; key
`finnhub_api_key` is read at `:128` but never declared in `config.load()` → effectively dead);
ForexFactory `https://nfs.faireconomy.media/ff_calendar_thisweek.json` `:169-206`. **Second,
duplicate fetcher:** `services/test_signal/news_filter.py:43-45` (same FF URL, own SSL context).

## 4. Licence / cluster

- Startup gate: `run.py:219-220` → `config/licence/guard.py:307 enforce()` — **fully offline**:
  reads `~/.forex_trader_licence` (`store.py:11`), verifies HMAC via `keygen.py:28
  verify_licence_key` (secret `keygen.py:17`, generator `generate_licence_key:21`), fingerprint,
  expiry (`guard.py:371-383`); failure exits via its own NiceGUI page on 8888. No dev flag.
- Phone-home only from the *registration screen*: `config/licence/client.py:15
  https://217.155.25.160` (cert-pinned).
- Cluster: remote admin `wss://217.155.25.160:8443` (`cluster/remote/tls.py:24`,
  `client.py:685`) — gated by `remote_admin_client_enabled`, **already default False**
  (`config/__init__.py:177-179`, `app.py:294-300`); node sync (`cluster/sync/*`, port 8765) —
  DB-flag gated, off by default; public-IP checks `cluster/remote/ip_check.py:24-26`.

## 5. Auth — none exists

Single page `frontend/app.py:709 @ui.page("/")`; no `storage_secret` in `ui.run`
(`run.py:262-277`); no login route. The app's own help text admits it
(`frontend/app.py:456`). Reusable password machinery: `services/cluster/remote/auth.py`
(scrypt `set_password:30`, `verify_password:40`, `password_is_set:55`; tested in
`tests/controllers/test_remote_admin_password.py`).

## 6. Config

Loader `backend/src/config/__init__.py:70 load()`; `_e()` at `:74-75` = **env wins over yaml**.
Data dir `:33-44`; `db_path = DATA_DIR/forex_trader_{account_env}.db` (`:182-186`). **No
.env/dotenv anywhere** — all raw `os.environ`. No existing `debug`/`dev_mode`/`test_mode` flag.
UI port: default 8890 in code (`:165`) vs 8888 in config.yaml.example — pre-existing wrinkle.

## 7. Frontend shell

`frontend/app.py` (1633 lines — over the 800 LOC gate already). Header/ticker row
`:889-1102` (54px row at `:893`, logo `:897-911`, BID/ASK `:926-932`); header refresh timer
`:1114/:1280`; tab nav `:1467-1533`; env switch `:1284-1412`. Pages talk to flat controllers
(`backend/src/controllers/*_controller.py`, 11 of them) — and `frontend/app.py` also reaches
`get_engine()` directly.

## 8. Composition root

`run.py:208 main()`: licence enforce → `_start_mt5_bridge()` → `cfg.load()` → `db.init` →
headless or `ui.run`. `backend/src/app.py:155 startup()`: `TradingRuntime(config)` `:170` (bridge
built inside), `TelegramReader` `:171`, engine `init(_engine._bridge)` `:176-196`, reader+runtime
startup `:207-212`, engine auto-start (DB-flag gated) `:216-250`, sync `:256-287`, remote admin
`:294-300`.

## 9. All other outbound network calls

| Purpose | Where | Destination |
|---|---|---|
| AI | `services/ai/provider.py:117,166,228` (Anthropic SDK), `:26,144` (DeepSeek) | api.anthropic.com / api.deepseek.com |
| Gold news RSS | `services/ai/claude_ai.py:134-137` | feeds.finance.yahoo.com |
| Model list refresh | `services/ai/model_refresh_loop.py` | Anthropic/DeepSeek |
| Email | `services/notifications/email_service.py:105,166` + SMTP | Resend / Mailjet / Gmail |
| Public IP | `cluster/remote/ip_check.py:24-26` | ipify et al. |

`tools/` has no network calls. AI provider already no-ops cleanly with no key
(`provider.py:50 is_configured`).

## 10. Existing test fakes (consolidation targets)

`tests/conftest.py:103 make_engine` — canonical injection point; its docstring already assumes
`_bridge=FakeBridge()` **but no shared FakeBridge exists** — instead 12+ per-file `_FakeBridge`
near-duplicates: `tests/core/test_ai_signal_fallback_*.py:52,58`,
`test_bot_commands_{infra,readonly,trading}_*.py:50-55`,
`test_bridge_process_relocation.py:62` (`_FakeNativeBridge`). HTTP-level fake template:
`tests/core/test_mt5_bridge_client.py:45-51`. Runtime shape guards that constrain the seam edit:
`tests/core/test_runtime_facade.py`, `test_runtime_dissolution_shape.py`,
`test_runtime_supervisor_shape.py`.
