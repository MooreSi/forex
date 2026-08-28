# 014 — Both TLS channels are encrypted but not authenticated

**Status:** found 2026-08-28 while writing tests for `sync/tls_util.py`. Not fixed.
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

## Not fixed here, deliberately

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
