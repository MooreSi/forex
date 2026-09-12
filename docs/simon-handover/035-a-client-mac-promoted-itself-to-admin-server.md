# Q035 — A client Mac promoted itself to admin server

**Who answers:** Simon.
**Status:** FIXED in code 2026-09-12 (option C below). Confirm the choice, or
say which of A/B/D you would rather have.

## What happened

The MacBook ("Mac", token `a94a16d2`, machine `FOREX-54821F39-…`) stopped
appearing as online in the Mac mini's admin console after it was restarted on
2026-09-12. The mini logged `[RemoteServer] Mac disconnected` at 07:42:59 and
nothing since.

It is not offline. It is running **the admin server** instead of the client.

Evidence gathered from the mini on 2026-09-12:

- `169.254.171.137:8443` (the MacBook, over the direct en10 link) completes a
  TLS handshake and presents a self-signed certificate `CN=217.155.25.160`,
  SAN `[IPAddress(217.155.25.160), DNSName(localhost)]` — the exact shape and
  SAN ordering `remote/tls.py::ensure_cert()` produces, and distinct from the
  `sync` certificate (port 8765, `DNSName` first).
- Its `not_after` is 2036-09-09 06:46 UTC, i.e. generated 2026-09-09. The only
  route to `ensure_cert()` is `server_ssl_context()`, which only the admin
  server calls.
- Its fingerprint differs from the mini's own server certificate (generated
  2026-09-02), so it is the MacBook's own, not a copied file.
- Port 8888 is closed there because the dashboard binds loopback
  (`run.py::_resolve_bind_host`) — so the app is up, just not as a client.

`app.py::startup()` is `if _should_start_remote_server(): … elif
_remote_client_enabled(config): …`. Server wins, so `_remote_client.start()`
never runs and the machine can never appear in the console.

## Why it promoted itself

`_should_start_remote_server()` is `LOCAL_ADMIN_AVAILABLE and
password_is_set()`. Both are plain filesystem facts on the client machine:

- `~/Documents/KeyGen/forex_admin.py` — and `~/Documents` is inside the iCloud
  Drive container on this Apple ID (Desktop & Documents syncing is on;
  confirmed `~/Library/Mobile Documents/com~apple~CloudDocs/Documents ->
  ~/Documents`), so KeyGen lands on every Mac signed in.
- `~/Library/Application Support/ForexTrader/remote/admin_password.hash` —
  `auth.password_is_set()` checks existence and non-zero size, nothing else.

The MacBook runs a build older than 2026-09-06, so it does not have the
`_is_somebody_elses_client()` guard at all.

Not proven, but consistent with the dates and with `app.py`'s own comments
about dataless KeyGen files: iCloud evicting and re-materialising
`forex_admin.py` makes this promotion **intermittent** — the machine is a
client on the launches where the file is not materialised at import time, and
a server on the launches where it is. That would explain both the 2026-09-09
certificate and the client connection that nevertheless ran until 07:42 today.

## The gap that remains after the 2026-09-06 fix

The `is_remote_client` marker demotes a machine that has **already received a
`MSG_WELCOME`**. A machine that has never been welcomed — or that was promoted
before it ever connected — still self-promotes on the strength of a synced
folder plus a local hash file. The marker is written by the very code path the
promotion prevents from running, so a machine that promotes on its first
launch can never write it.

## The question

How should a machine decide it is the licence issuer? Options, none
implemented:

- **A.** Leave it. The marker covers machines that have connected once, and the
  operational fix is to remove `admin_password.hash` from client machines.
- **B.** Keep KeyGen out of iCloud (move it to a non-synced path on the mini)
  and treat its presence elsewhere as the accident it is.
- **C.** Pin the issuer to hardware — the mini's fingerprint is
  `FOREX-349E9267-EBB61E27-539D9A41-3AAC333E` — so no other machine can be the
  server whatever is on its disk.
- **D.** Require an explicit opt-in file written only by KeyGen's "Setup Admin
  Server" script, rather than inferring from the folder.

**ANSWER:** C, implemented — you asked for a fix that needs nothing typed on
the MacBook, and C is the only one of the four that qualifies. A and B both
require touching the client machine; D requires re-running a KeyGen script
there.

## What was done

`backend/src/config/licence/issuer.py` pins the issuer to hardware:

```
ADMIN_MACHINE_FINGERPRINT = "FOREX-349E9267-EBB61E27-539D9A41-3AAC333E"
```

That is the Mac mini's `get_fingerprint()`. Two callers now lead with it:

- `app.py::_find_admin_open_fn()` — no local KeyGen console anywhere else, and
  because `LOCAL_ADMIN_AVAILABLE` is derived from it, no admin server either,
  so the machine stays on the client side of `startup()`'s choice.
- `config/licence/guard.py::_this_is_the_admin_machine()` — the activation
  screen brings up the client, not the issuer, on every other machine.

It lives under `config/licence/` because `config/` is the bottom of the import
stack and `guard.py` may not reach up into `services/`.

### The lockout question

Pinning to `get_fingerprint()` adds no fragility the licence does not already
carry: the licence itself is keyed to that value, so a Mac mini whose
fingerprint drifts has lost its licence regardless. If you ever replace or
reimage the mini, either set `FOREX_ADMIN_MACHINE_FINGERPRINT` in the
environment or change the constant and push — both are done on the mini, which
is the machine you can always reach.

### What it does not fix

The MacBook must also be back on the 192.168.0.0/24 LAN. On 2026-09-12 it had
only a self-assigned `169.254.171.137` on the direct cable, and from there the
beacon cannot reach it, the subnet scan derives the wrong `/24`, and the WAN
fallback needs internet. Rejoining the WiFi is enough; no terminal.
