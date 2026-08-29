# 014 — Both TLS channels are encrypted but not authenticated

**Status:** found 2026-08-28 while writing tests for `sync/tls_util.py`.
**SYNC CHANNEL FIXED the same evening — see the bottom. The licence/admin
channel (`remote/tls.py`, `remote/client.py`) is still unauthenticated.**
**Touches money:** indirectly — the sync channel carries trade state between
nodes, and the remote channel carries licence issuance.
**Severity:** needs an attacker on the network path. Not remotely triggerable
on its own, and both endpoints are fixed IPs the owner controls.

## What is wrong

Both cluster channels build their client SSL context like this:

```python
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode    = ssl.CERT_NONE
```

That is a normal pattern for a self-signed server on a bare IP, and it is safe
**only** when the client then compares the presented certificate against a
fingerprint it already knows.

`sync/tls_util.py`'s own docstring says exactly that:

> "the caller is responsible for checking the fingerprint against the pinned
> value (see client.py's `_verify_fingerprint`) since hostname/CA checks are off"

**`_verify_fingerprint` does not exist.** The only occurrences of that name in
the repository are that docstring and the test that now records this. Nothing
calls `getpeercert()`. `cert_fingerprint()` is read in exactly two places: a
log line when the sync server starts, and the Remote Node screen that displays
the value to the user.

So the fingerprint is generated, stored, logged and displayed — and never
compared to anything.

## Why it matters

`sync/client.py::_connect_once` opens the socket and immediately sends its
shared token:

```python
async with websockets.connect(uri, ssl=ctx, ...) as ws:
    await ws.send(json.dumps(make(MSG_HELLO, token=self._token)))
```

The token authenticates the CLIENT to the SERVER. Nothing authenticates the
server to the client. Anyone able to intercept that connection — or redirect
the VPS IP — can present any certificate, have it accepted, and receive the
token on the first frame. They can then use it against the real VPS.

`remote/tls.py` has the same shape on the licence/admin channel.

## Why it was not fixed immediately

Certificate pinning done badly is worse than none — a wrong comparison that
always passes looks identical to a working one. This is also the licence
channel, which CLAUDE.md puts behind owner sign-off.

What a fix would involve, for whoever picks it up:

1. After connect, read the peer certificate (`ws.transport.get_extra_info(
   "ssl_object").getpeercert(binary_form=True)`), SHA-256 it, and compare
   against the value the user pinned in Settings > Remote Node.
2. Close the connection BEFORE sending the token if it does not match. The
   token must not leave the machine until the peer is proven.
3. Decide first-connect behaviour — trust-on-first-use, or require the user to
   type the fingerprint the VPS printed. TOFU is friendlier and still leaves
   the first connection exposed.
4. A mismatch must fail loudly and stay failed. Silently reconnecting would
   turn an attack into "the sync is flaky".

## Current state in the suite

`tests/core/test_sync_tls_util.py` asserts the settings as they are today, with
the gap written into the test name and docstring, so it is visible rather than
resting on a docstring that promises a safeguard nobody wrote. That test should
be changed as part of fixing this.

## How it was found

By writing tests. The first version of that test asserted the configuration was
safe and cited `_verify_fingerprint` as the reason — repeating the docstring's
claim without checking it existed. Grepping for the function to reference it
properly is what turned this up.

---

## Fixed for the sync channel, 2026-08-28

### What it does now

`_connect_once` verifies the peer **before** the token is sent:

```python
_ok, _why = tls_util.verify_or_pin(self._host, tls_util.peer_fingerprint(ws))
if not _ok:
    self.conn_state = CONN_REJECTED
    ...
    return
self._ws = ws
await ws.send(json.dumps(make(MSG_HELLO, token=self._token)))
```

Trust-on-first-use: the first fingerprint seen for a host is stored in
`app_config` and accepted; every later connection must match it. A mismatch is
refused, the pin is **not** overwritten, and the connection state goes to
`CONN_REJECTED` so it stays refused rather than quietly retrying into an
interception.

TOFU is what makes this safe to ship to an already-paired Mac/VPS: the first
connection after the upgrade pins whatever they are already talking to, so
nothing breaks. **The first connection is still exposed.** That is the known
limit of trust-on-first-use, and it is stated here rather than papered over.

### Recovery

`ensure_cert()` never rotates a certificate that already exists, so a mismatch
should mean something is wrong. If the VPS certificate genuinely was reissued,
re-entering the connection details in **Settings > Remote Node** clears the pin
and pairs again — `SyncClient.configure()` calls `clear_pin()`. That is the
only route back, and it is deliberately the same action a user would already
take, rather than a hidden flag. The refusal message says so.

### The part that could have been faked, and was not

`peer_fingerprint()` reaches through a websockets internal
(`ws.transport.get_extra_info("ssl_object").getpeercert(binary_form=True)`).
A mocked test would pass while that path was wrong — which is the exact shape
of the original bug, a safeguard that looked present and was not. So it is
proved against a **real TLS handshake**: the test starts a local websocket
server using this app's own `server_ssl_context()`, connects with its own
`client_ssl_context()`, and asserts the fingerprint read off the live
connection equals `cert_fingerprint()`.

### Also proved

Ten mutants, all killed, including the two that matter most: verification
skipped entirely, and verification moved to **after** the token is sent. The
second is the whole point — pinning that happens after the token leaves is
worth nothing.

### A note on the LOC ratchet

`sync/client.py` is shrink-only and the guard pushed it 867 -> 888. Rather than
raise the baseline, the pending-proposal persistence was moved verbatim into
`sync/_pending_store.py` as a mixin (a pure move — same methods, same bodies,
covered by the 24 tests in `test_sync_pending_proposals.py`), bringing the file
to 823. No baseline was raised.

## Still open: the licence/admin channel

`remote/tls.py` and `remote/client.py` have the identical hole and are **not**
fixed. The same primitives apply, but that channel carries licence issuance and
admin authority, and its client is the one an admin uses to recover a stranded
install — a pin that refuses wrongly there locks someone out of the recovery
path itself. That trade-off wants your decision before I wire it, so
`tests/remote/test_remote_tls.py` still records the gap as it stands.
