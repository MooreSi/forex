# 010 — Certificate pinning for the remote-admin channel

**Status:** not started
**Raised:** 2026-08-26, from Q001 #5 (amended) in docs/simon-handover/
**Touches money:** no — but it is the last unauthenticated link to the fleet
**Depends on:** nothing

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
