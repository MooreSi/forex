# What happened on the evening of 2026-08-28

You were out. This is what got done, what it found, and the two things that
now need you. Nothing was placed, closed or modified on any account.

## Needs a decision from you

**1. [bugs/014](../todo/bugs/014-sync-and-licence-tls-are-unauthenticated.md) —
both TLS channels are encrypted but not authenticated.** The sync channel and
the licence/admin channel both accept any certificate. `tls_util`'s own
docstring says the client pins the fingerprint via `client.py::_verify_
fingerprint`; **that function does not exist** anywhere in the tree, nothing
calls `getpeercert()`, and the fingerprint is only ever logged and shown on
screen. The sync client sends its auth token on the first frame after that
unverified handshake.

Not fixed on purpose. Pinning done badly is worse than none — a comparison that
always passes looks identical to a working one — and it is the licence channel.
014 sets out what a fix involves, including the two parts easy to get wrong.

**2. [bugs/015](../todo/bugs/015-bare-direction-message-is-rescanned-forever.md)
— half fixed, half needs you.** A bare "XAU USD SELL" with no levels was
re-parsed and re-logged about once a second for hours: 8,319 identical lines
from one message. The logging is fixed. The *re-parsing* is not, because
stopping it means recording the message as a parked signal, and that changes
what the follow-up matcher can find. That is a decision about how a bare
direction should be treated, not a cleanup.

Still open from earlier: **[009](009-breached-zone-discard-or-queue.md)** —
breached-zone signals are discarded, not queued.

## M2 is verified

The Telegram panel's IME toggle (bug 012) works. A real bare SELL arrived from
Gold Diggers VIP at 16:41 with `immediate_market_entry = 0`: **no market order,
no database row, no alert.** The contrast cases from when IME was on are still
in the table (`instant_activated`).

Only half of M2 is verified. "Toggle on, repeat, confirm it fires" needs a
market order placed, which is your call. M3–M7 are untouched.

One thing to know for next time: **there is no log line when a risk setting
changes**, so the moment IME was switched off cannot be established from the
log — only its current value from the database.

## Tests

The cluster campaign you deferred is largely done. Coverage of
`services/cluster` went from the high-20s/30s on the big files to **53% for the
package**, and the suite is now over 4,000 tests.

Covered tonight: licence issuance/revocation and admin authority, the admin
command handler, the sync token gate and handshake, stand-down/resume,
forwarded order handling, client machine identity, both TLS modules, the
consolidated ledger, the cross-engine signal bus, node roles, mirrored peer
data, the self-healer, and the startup licence gate.

Every one was mutation-tested — the source was deliberately broken in specific
ways and each break had to make a test fail. The mutants and their results are
named in each commit. Three of my own tests were too weak to catch their mutant
and were rewritten; two more were simply wrong and the code was right. That is
all written down in the commits rather than tidied away.

## Two things that were found and NOT changed

- `node_roles.is_active_trader_node()` does not fail open despite its docstring
  saying it does. It catches `ImportError` only, so a database error propagates
  and the effect is fail-CLOSED. Pinned by a test named for the mismatch.
- Approving a client with the licence signer unregistered **succeeds**, adding
  the token to the allowed list with an empty licence key — trusted by the
  server while holding nothing that validates offline. Also pinned, not
  changed: it is a licensing policy call.

## Note

The running app still has the pre-fix code loaded, so the bugs/015 log spam
continues until it is restarted.
