# 010 — Certificate pinning for the remote-admin channel

**Status:** **RESOLVED 2026-09-02**, by the work recorded in
[bugs/014](../bugs/014-sync-and-licence-tls-are-unauthenticated.md), which
reached this channel from the other direction and closed it. This file was left
saying "not started" until 2026-09-05 and was wrong for three days — see
*Reconciled* at the bottom for what was actually built against what is proposed
below, and for the one loose end the reconciliation found.
**Raised:** 2026-08-26, from Q001 #5 (amended) in docs/simon-handover/
**Touches money:** no — but it *was* the last unauthenticated link to the fleet
**Depends on:** nothing

> Everything from here to *Reconciled* is the 2026-08-26 proposal, kept
> unedited because the option that was chosen is not the one recommended here
> and the reasoning is worth having side by side.

## Problem

The remote-admin client connects to the admin server over TLS with verification
switched off:

    backend/src/services/cluster/remote/tls.py
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

So the client will complete a TLS handshake with *anything* that answers. Someone
on the network path between a client and the admin server can present their own
certificate and be accepted.

This is now the **only** unauthenticated part of that channel. The two bigger
holes closed on their own:

* Upstream `0815cc6` deleted the zip-streaming push. An admin "update" is now a
  `MSG_GIT_UPDATE` trigger asking the client to run its own git pull, so an
  impersonator can no longer hand over arbitrary code.
* Upstream `062b2be` fixed LAN discovery, which previously accepted any host on
  the subnet with port 8443 open — a router or NAS answered that probe as
  readily as the real server. A candidate must now complete a WebSocket
  handshake first.

## Why it is not already done

Upstream tried and stopped, and its reasoning still stands
(`062b2be`): *"The cert cannot be pinned client-side (the fingerprint file only
ever exists on the server machine, and the client runs CERT_NONE)."*

Pinning therefore needs a way to get the fingerprint **to** the client, and that
is the actual design problem — not the pinning code, which is a few lines.

## Options, with the trade-off stated

1. **Ship the fingerprint with the licence.** The client already receives a
   signed licence from the admin server, and that payload is Ed25519-signed with
   a key the client can verify. Adding the server's certificate fingerprint to it
   makes the pin arrive over a channel that is already authenticated. Best fit
   for the existing design; needs a licence-payload change on both sides.
2. **Pin on first use (trust-on-first-connect).** Store the fingerprint the first
   time a client connects and refuse a change after that. No protocol change, and
   it closes the ongoing risk — but the very first connection is still open, which
   is the connection an attacker would target for a new install.
3. **A proper CA.** Correct and standard, and disproportionate for a fleet of
   this size with no existing PKI.

Recommendation: **(1)**, with **(2)** as the interim if the licence change has to
wait — (2) alone is a real improvement over CERT_NONE.

## What must NOT change

* Simon's existing clients must keep connecting. A pin that locks the fleet out
  is worse than the risk it removes — this needs a rollout that tolerates
  unpinned clients until they have a pin.
* The licence-signing private key stays outside this repository.

## Tests first

* `tests/controllers/test_remote_tls_pinning.py::test_a_mismatched_fingerprint_is_refused`
* `::test_a_matching_fingerprint_connects` — negative control
* `::test_a_client_with_no_pin_yet_still_connects` — the rollout guarantee
* `::test_the_pin_survives_a_restart`

## Done when

Verification is on, a mismatched certificate is refused with a clear log line,
existing clients still connect, and `app.py`'s remote-client warning no longer
has to name the unpinned certificate — because there isn't one.

---

## Reconciled, 2026-09-05

This file and `bugs/014` described the same channel and disagreed: one said
"not started", the other said "fixed 2026-09-02". **The code is the fact, and
the code agrees with 014.** `remote/tls.py` carries `is_ca_verified()`,
`client_ssl_context(host)` and `peer_is_acceptable()`, and
`remote/client.py:520` calls `peer_is_acceptable(host, peer_fingerprint(ws))`
before the hello that carries the licence token. The `CERT_NONE` block this
file quotes still exists, but only as the LAN branch, and the application layer
now checks that branch.

### Against the options above

Neither 1 nor 2 alone. The owner chose (2026-09-01) **a private CA for the
internet path and trust-on-first-use for the LAN** — so option 3, ruled out
here as "disproportionate", is what the internet path actually got, and option
2 covers the LAN. Option 1, shipping the fingerprint with the licence, was not
built: the licence payload is unchanged.

The reason 3 stopped being disproportionate is that the fleet has one fixed
public address. The CA mints one certificate for `217.155.25.160`; there is no
PKI to run.

### Against "Done when"

| This file's bar | State |
|---|---|
| Verification is on | Yes — CA on the internet path, TOFU pin on the LAN |
| A mismatch is refused with a clear log line | Yes — `verify_or_pin` refuses and does not overwrite the pin |
| Existing clients still connect | Yes — TOFU pins on first sight; the internet path went straight to CA-verified in one build, deliberately, so no client was ever pinned to the self-signed certificate |
| `app.py`'s warning no longer names the unpinned certificate | **This was still open.** Fixed 2026-09-05, below. |

### The loose end this reconciliation found

`backend/src/app.py::_remote_client_enabled` logged, on every boot with the
remote client enabled, that the link "runs TLS with certificate verification
DISABLED and no certificate pinning" and that "certificate pinning is the
tracked fix". All three claims were false from 2026-09-02. That function's own
docstring argues that a warning naming a risk which no longer exists trains
people to ignore warnings — so it had become the failure it was written to
prevent.

Rewritten to name what actually remains: the internet path is CA-verified, and
on the LAN the certificate is trusted on first sight, so that first connection
alone can be impersonated. `tests/controllers/test_remote_client_default.py`
was rewritten with it — the assertions are now the opposite of what they were,
and three of them are absences (`"verification disabled"`, `"no certificate
pinning"`, `"pinning is the tracked fix"`), because the failure being guarded
is text that survives the fix it describes. All three were watched failing
against the old warning before the new one was written.

### What is still owner-side

Not a code gap, but the pieces this closure rests on:

- The server certificate expires 2028-12; the CA in ten years. Reissue with
  `make_remote_ca issue` and **restart the admin server** — until the restart
  it keeps presenting the old self-signed certificate.
- `ca_key.pem` stays outside the repository. Whoever holds it can mint a
  certificate this app trusts. Three tests in `tests/remote/test_bundled_ca.py`
  check it is absent, untracked, and would be refused by `git check-ignore`.
- TOFU's first LAN connection remains exposed. That is the known limit of the
  mechanism, stated rather than papered over, and it is what the boot warning
  now says.
