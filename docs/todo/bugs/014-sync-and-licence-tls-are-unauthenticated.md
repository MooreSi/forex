# 014 — Both TLS channels are encrypted but not authenticated

**Status:** found 2026-08-28 while writing tests for `sync/tls_util.py`.
**BOTH CHANNELS NOW FIXED.** The sync channel the same evening; the
licence/admin channel on 2026-09-02, on the owner's instruction to finish it.
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

## Closed: the licence/admin channel, 2026-09-02

The owner's decision, 2026-09-01: **a private CA for the internet path, and
trust-on-first-use for the LAN.** Both are now live.

### What it does now

`client_ssl_context(host)` returns one of two contexts:

| Path | Context | Who establishes the peer |
|---|---|---|
| `217.155.25.160` (the public address) | `CERT_REQUIRED`, `check_hostname=True`, verified against the bundled `ca_cert.pem` | the TLS handshake itself |
| anything else — LAN, localhost | `CERT_NONE` | `peer_is_acceptable` -> `verify_or_pin`, pinned on first sight |

`peer_is_acceptable` short-circuits to True on a CA-verified connection.
Demanding a fingerprint on top would refuse a connection TLS has already
authenticated.

The hello sent immediately after connecting carries the licence token, the
machine UUID and the hostname, so the peer had to be established *before* it
goes out — which is what stage 2 rearranged and what this stage now makes
meaningful.

### Why no trust-on-first-use on the internet path

Deliberate. Pinning the self-signed certificate there would mean that the day
the CA-signed one is deployed, every already-updated client sees a mismatch and
refuses — a lockout created by the upgrade itself. That path goes straight from
unauthenticated to CA-verified in one build.

### The rollout, in the order it had to happen

Bundling the authority before the server presented a CA-signed certificate
would have refused every internet client at once, so:

1. `make_remote_ca init --dir ~/forex-admin-ca` — outside the repo.
2. `make_remote_ca issue --address 217.155.25.160` — the server certificate.
3. Verified the chain against the CA **before installing anything**.
4. Installed the pair into `USER_DATA_DIR/remote/`, keeping the self-signed
   one in `selfsigned-backup-<timestamp>/` as the way back.
5. Re-verified end to end through the app's own `server_ssl_context()` and
   `client_ssl_context()`: `verify_mode=CERT_REQUIRED`, `check_hostname=True`.
6. Only then copied `ca_cert.pem` into the source tree.

### The private key

`ca_key.pem` never enters the repository. Anyone holding it can mint a
certificate this app trusts without question — a strictly worse position than
the unauthenticated channel this replaced, which at least required being on the
network path. It is gitignored, and three tests in
`tests/remote/test_bundled_ca.py` check it is absent from the tree, untracked,
and that `git check-ignore` would stop it being added.

### One thing only mutation testing found

`is_ca_verified` is `host == SERVER_HOST and bundled_ca_path() is not None`.
Dropping the second half changes nothing today, because a CA *is* bundled — so
the mutant survived. It matters for every build made **before** the cutover:
without the guard such a build would announce that TLS had established the
peer, skip `verify_or_pin` entirely, and send the licence token to anything
that answered. Now covered by
`test_a_build_with_no_authority_does_NOT_claim_verification`.

### Note on the existing test

`test_the_client_context_does_not_verify_and_NOTHING_PINS_THE_CERT` asserted
the gap on purpose, and said in its own docstring that it should change when
014 did. It has been replaced, not bent to fit — the assertions are now the
opposite, plus a new one that stands a self-signed impostor for the right
address in front of the client and requires the handshake to fail.

### Still owner-side

The server certificate expires in 825 days (2028-12); the authority in ten
years. Reissue with `make_remote_ca issue` and restart the admin server.
**The app must be restarted to serve the new certificate** — until then it
presents the old self-signed one, which only affects clients built after this
change.
