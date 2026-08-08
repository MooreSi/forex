# Security & Operations Review — FOREX Trader (live-money MT5)

- **Date:** 2026-08-08
- **Reviewer:** Defensive security/ops review (owner-authorized, read-only)
- **Scope:** Network exposure, cluster/remote & sync services, secrets handling, Telegram integration, installer/update path, logging, dependencies, licence mechanism.
- **Method:** Static read-only source review. The app was never run; MT5 was never touched.

> Note on checkout: this is the `forex-refactor2` fork. Some paths referenced in
> older docstrings (e.g. `forex_trader/…`, `remote/server.py`) now live under
> `backend/src/…`. File:line references below are against the current tree.

---

## Summary

The single most serious issue is that the trading dashboard — which can place,
close and modify real-money orders and change every risk setting — is served on
**`0.0.0.0:8888` with no authentication of any kind**. Anyone who can reach that
port (any device on the same LAN, or anything routed to it) has full control of a
live trading account. The app's own setup text acknowledges this ("it has no
separate login of its own") and relies entirely on the operator never exposing
the port — a fragile control for a money-moving system.

The second critical issue is the **remote update channel**: the update client
accepts a code package (a ZIP that is written over the app and executed on
restart) protected only by a SHA-256 that travels in the same message as the
payload, over a TLS connection whose certificate is **never verified** (`CERT_NONE`,
`check_hostname=False`, no fingerprint pinning). Worse, the client **discovers its
update server via an unauthenticated UDP LAN broadcast beacon** (and a TCP subnet
scan fallback). Any device on the LAN can impersonate the update server and push
arbitrary code — remote code execution on the trading host. There is no
code-signing anywhere in the update path.

On the positive side: no unsafe deserialization was found (all wire payloads are
`json.loads`, not pickle/yaml/eval); no real secrets are committed to the repo
(the config template is clean, and live secrets live outside the repo, encrypted);
Telegram bot commands are gated to a single configured `chat_id`; and the sync
trade-command channel is token-authenticated with a constant-time comparison.

---

## Attack surface map

| Surface | Bind / reach | Auth | Transport | What it can do |
|---|---|---|---|---|
| Web dashboard (NiceGUI) | `0.0.0.0:8888` (`run.py:263`) | **None** | Plain HTTP | Place/close/modify live orders, change all risk settings, switch live/demo, edit credentials |
| Remote update client | Outbound to `wss://217.155.25.160:8443` **or LAN-discovered IP** (`remote/client.py:673-694`) | Server not authenticated by client | TLS **unverified** (`remote/tls.py:90-95`) | Receives ZIP → overwrites app files → runs `pip install` → restarts (RCE) |
| LAN discovery beacon | UDP broadcast `:8444`, TCP scan of /24 (`remote/client.py:59-150`) | **None** | Cleartext UDP | Redirects update client to attacker-chosen host |
| Remote admin server | `0.0.0.0:8443` (`remote/server.py:1169-1179`) | scrypt password + macOS IOKit UUID allowlist; **external-IP gate** to start | TLS (self-signed) | Approve/revoke licences, push updates to all clients |
| Sync server (VPS) | `0.0.0.0:<8765>` (`sync/server.py:212-215`) | Shared token, `secrets.compare_digest` (`sync/server.py:227-231`) | TLS (self-signed) | Place market/signal orders, stand-down/resume trading, change synced risk settings on the VPS |
| Sync client (Mac) | Outbound to user-entered VPS IP (`sync/client.py:242-250`) | Sends shared token | TLS **unverified**, **no fingerprint pinning** | Leaks sync token to a MITM |
| Telegram bot (getUpdates) | Outbound long-poll | Single `chat_id` allowlist (`telegram/bot_loop.py:122`) | HTTPS to Telegram | `/close`, `/marketbuy`, `/marketsell`, `/restartapp` + read-only cmds |
| MT5 bridge | `localhost:9000` (config default) | None (localhost) | Plain HTTP | Order placement bridge |

---

## Findings (by severity)

### CRITICAL

**C1. Web dashboard has no authentication and binds to all interfaces.**
`run.py:262-277` calls `ui.run(host="0.0.0.0", port=port, …)` with no auth, no
`storage_secret`, and no middleware. The root page `@ui.page("/")`
(`frontend/app.py:709`) is served to anyone who connects. The dashboard can open
and close real-money trades, change risk governors, switch the account between
demo and live, and enter broker credentials. Anyone on the LAN (or anyone who can
reach a forwarded/misconfigured port) has full control of the live account. The
licence gate (`config/licence/guard.py`) also runs its blocking screens on
`0.0.0.0:8888` (`guard.py:56, 300`), so it is not an access control for the app.
The app's own setup guidance concedes this: *"Do not open port 8888 to the
internet — that's the app's own dashboard and it has no separate login of its
own"* (`frontend/app.py:456`).
**Impact:** Complete takeover of a live trading account by any LAN-adjacent actor.
**Recommendation:** Bind to `127.0.0.1` by default; require an explicit opt-in to
expose. Add an authentication layer (NiceGUI `storage_secret` + a login page, or a
reverse proxy with auth) before any non-loopback bind is permitted.

**C2. Remote update path allows unauthenticated remote code execution.**
The update client (`remote/client.py`) applies a pushed ZIP by extracting it and
overwriting live app files, then running `pip install` and restarting
(`_apply_update`, `remote/client.py:504-668`). The only integrity check is a
SHA-256 that is sent **in the same `MSG_UPDATE_BEGIN` message as the payload**
(`remote/client.py:512-514, 817-822`) — it detects corruption, not forgery. There
is **no code signature**. The connection's TLS certificate is **not verified at
all**: `client_ssl_context()` sets `check_hostname=False` and
`verify_mode=CERT_NONE` (`remote/tls.py:90-95`), and the client never checks the
fingerprint that `tls.py` generates. The client also **finds its server via an
unauthenticated UDP broadcast beacon** on `:8444` and a TCP `/24` scan
(`remote/client.py:59-150, 683-685`), then connects to whatever IP it hears and
accepts a `MSG_WELCOME` from it without authenticating the server. A malicious
device on the LAN can therefore broadcast a beacon, accept the client's
connection, and stream an arbitrary ZIP → arbitrary code execution on the trading
host as the app user.
**Impact:** Full RCE on a live-trading machine from any LAN-adjacent attacker
whenever the update client is running (it runs during first-run/licence activation
regardless of the opt-in, and always when `remote_admin_client_enabled=true`).
**Recommendation:** Sign update packages (asymmetric signature over the ZIP +
version, public key shipped in-app) and verify before applying; pin the server
certificate fingerprint (the value already exists via `cert_fingerprint()`);
authenticate the server before accepting `MSG_WELCOME`; and drop or authenticate
the LAN beacon/scan discovery.

### HIGH

**H1. Sync client does not verify the server certificate or pin its fingerprint.**
`sync/client.py:242-250` uses `tls_util.client_ssl_context()` which is `CERT_NONE`
/ `check_hostname=False` (`sync/tls_util.py:91-98`). The docstring there claims the
caller checks the fingerprint "see client.py's `_verify_fingerprint`", but **no such
check exists** in `sync/client.py` (no fingerprint/pin code is present). The client
then sends the shared sync token in `MSG_HELLO` to whatever endpoint answers. A
network MITM (ARP/DNS spoof, hostile Wi-Fi, compromised upstream) can transparently
intercept, capture the sync token, and thereafter drive the real VPS's trade
commands (`MSG_MARKET_ORDER`, `MSG_SIGNAL_ORDER`, `MSG_STAND_DOWN`).
**Recommendation:** Implement the fingerprint pinning the docstring already
promises, and refuse to send the token until the server cert matches the pinned
value entered in Settings > Remote Node.

**H2. Licence HMAC secret is hardcoded and shipped to every client.**
`config/licence/keygen.py:17` — `_SERVER_SECRET =
b"FOREX-SERVER-SECRET-CHANGEME-BEFORE-PRODUCTION"`. This same secret both generates
and verifies licences (`generate_licence_key` / `verify_licence_key`), and it is
present in the code distributed to every user. Anyone with a copy of the app can
compute a valid perpetual licence for their own machine ID — the licence mechanism
provides no real enforcement against a determined user. It also still carries the
literal `CHANGEME-BEFORE-PRODUCTION` marker. (See "Licence mechanism" note below —
this is inherent to a symmetric offline scheme; CLAUDE.md forbids adding a bypass,
so this is reported, not "fixed".)
**Recommendation:** If licence robustness matters, move to asymmetric signing
(private key stays with the admin/KeyGen; only a public verification key ships).
At minimum rotate the secret away from the placeholder. Treat licensing as
anti-casual-copy only, not a security control.

### MEDIUM

**M1. Remote admin server relies on an external-IP check as a start-time gate.**
`remote/server.py:1141-1185` refuses to start unless the machine's WAN IP equals
`217.155.25.160` (`ip_check.is_admin_machine`, fetched from third-party IP-echo
services). This is a reasonable belt-and-braces control, but external IP is
attacker-influenceable in some network positions and depends on external HTTP
services being reachable and honest. It should not be the sole thing standing
between an attacker with the (scrypt-hashed) admin password file and the admin
server. The actual admin auth (scrypt password + IOKit UUID allowlist,
`remote/auth.py`, `remote/server.py:684-722`) is sound; the concern is treating the
IP gate as a security boundary.
**Recommendation:** Keep the IP gate as defense-in-depth but document that admin
security rests on the password + UUID allowlist, and ensure the password file is
never distributed (it currently lives in `USER_DATA_DIR`, which is correct).

**M2. Admin password transmitted in-band and self-signed cert not pinned by the admin client.**
`MSG_ADMIN_HELLO` sends the admin password "plain, over TLS" (`remote/protocol.py:35`).
Because the server cert is self-signed and clients in this codebase use `CERT_NONE`
contexts, a MITM against the admin console connection could capture the admin
password. Combined with H1's pattern, unverified TLS is systemic.
**Recommendation:** Pin the admin server cert fingerprint in the admin client;
consider a challenge/response instead of sending the password.

**M3. Update client runs `pip install` from an attacker-controllable requirements.txt.**
Within `_apply_update` (`remote/client.py:603-624`), after files are overwritten the
client runs `pip install -r requirements.txt` using the just-written file. If C2 is
exploited (or the legitimate server is compromised), this is a second code-execution
vector (malicious/renamed package pins) independent of the Python files.
**Recommendation:** Covered by signing the package (C2); additionally pin/lock
dependencies and validate `requirements.txt` against an allowlist before install.

**M4. Dependencies are floor-pinned (`>=`), not locked.**
`requirements.txt` uses `>=` for everything (e.g. `anthropic>=0.36.0`,
`nicegui>=1.4.0`, `PyYAML>=6.0`). Combined with M3's `pip install` on update, a
build can silently pull newer/compromised transitive versions. No hashes, no lock
file.
**Recommendation:** Add a lockfile (pip-tools/`requirements.lock` with `--require-hashes`)
for the deployed environment.

### LOW / INFORMATIONAL

**L1. Diagnostics upload includes raw application logs.** `_build_diagnostics`
(`remote/client.py:357-393`) sends up to ~3000 raw log lines to the admin server on
request. This is a legitimate support feature, but it means whatever the logs
contain (see L2) leaves the machine. Ensure logs are scrubbed (see L2) so this
channel cannot leak credentials.

**L2. Logging hygiene — no committed leaks found, but verify at runtime.** The
`latest_logs/` and `archived_logs/` directories are empty in this checkout, so no
leaked secrets could be confirmed or refuted here. Code paths generally log
account/trade metadata (trade IDs, directions, balances) and mask keys in at least
one place (`sync/server.py:787` masks `*_key`). Credentials are stored under
`*_enc`/keychain and referenced by handle. **Action:** spot-check a live
`forex_trader.log` for account numbers, broker passwords, Telegram tokens, and API
keys before shipping diagnostics anywhere, and confirm the diagnostics uploader
never includes the credential store.

**L3. No unsafe deserialization (positive finding).** All remote/sync/beacon
payloads are parsed with `json.loads`; update/model archives use `zipfile`. No
`pickle`, `yaml.load` (unsafe), `eval`, `exec`, or `marshal.loads` on remote input
was found. (The `.exec(...)` hits in the grep are the SQLite adapter's method name,
not `exec()`.)

**L4. Secrets handling is sound (positive finding).** `config.yaml.example` ships
with empty values and no credentials; real config lives outside the repo in
`USER_DATA_DIR`; a repo-wide scan for embedded API keys/passwords/tokens returned
nothing beyond the licence placeholder (H2). Sync deliberately allowlists which
settings cross the wire and excludes MT5 credentials and `anthropic_api_key`
(`sync/server.py:82-84, 763-770`).

**L5. Telegram command auth is present but coarse.** The bot only acts on messages
whose `chat_id` equals the single configured `chat_id` (`bot_loop.py:122`), and only
that chat can trigger `/close`, `/marketbuy`, `/marketsell`, `/restartapp`
(`bot_dispatch.py:74-77`). This is adequate if the bot token and chat stay private,
but there is no per-command confirmation for money-moving commands and no second
factor — anyone who obtains the bot token or is added to that chat can trade.
Inbound signal-group messages drive automated trading by design (the app's core
copy-trading function); that is expected behavior, not a defect, but it means the
Telethon session and signal-group membership are trust-critical.

---

## Recommendations (prioritized)

1. **(C1) Stop binding the dashboard to `0.0.0.0` without auth.** Default to
   `127.0.0.1`; gate any wider bind behind an authenticated login. This is the
   highest-value, lowest-effort fix.
2. **(C2) Make the update path authenticated and signed.** Asymmetric signature
   over the package, cert-fingerprint pinning, server authentication before
   accepting `MSG_WELCOME`, and removal/authentication of the LAN beacon discovery.
3. **(H1) Implement the missing sync-client fingerprint pinning** before the token
   is ever sent.
4. **(H2) Re-architect licensing to asymmetric signing** (or accept it as
   anti-casual-copy only and rotate the placeholder secret).
5. **(M2) Pin the admin server cert** in the admin client and avoid sending the
   admin password in-band.
6. **(M3/M4) Lock dependencies with hashes** and validate `requirements.txt` on
   update.
7. **(L2) Add a log-scrubbing pass** and verify the diagnostics uploader excludes
   credentials.

---

## Open questions

1. What is the intended deployment topology for port 8888 — is it ever reachable
   beyond `localhost`/RDP in practice? If strictly RDP-only, C1's residual risk is
   LAN-only but still real (other LAN devices, RDP over an untrusted network).
2. Is `remote_admin_client_enabled` expected to be on for normal users, or only
   during first-run activation? This determines how continuously C2 is exposed.
3. Does the live `forex_trader.log` contain broker account numbers, passwords, or
   Telegram/API tokens? (Could not be confirmed — log dirs empty in this checkout.)
4. Is the sync token ever entered/transported over untrusted networks (setup time)?
   That is when H1's token-leak risk is highest.
5. Has `_SERVER_SECRET` ever been rotated from the `CHANGEME-BEFORE-PRODUCTION`
   placeholder in the shipped builds, and does the KeyGen tool use the same value?
6. Are the self-signed sync/remote certs regenerated per install, and is the
   fingerprint communicated to operators out-of-band so pinning (once added) is
   trustworthy on first connect?
