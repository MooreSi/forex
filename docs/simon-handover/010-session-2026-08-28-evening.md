# What happened on the evening of 2026-08-28

You were out. Nothing was placed, closed or modified on any account.

**Two of the three bugs are now fixed** (016 and the sync half of 014), plus the
log half of 015. What is left needs a decision from you rather than more work.

## Fixed while you slept

| | What | Effect |
|---|---|---|
| **016** | A placeholder the broker has never heard of is now written off after 24h (a new Expert Tunable) | Gets your lost trade slot back, and stops it happening again |
| **014** | The sync channel now pins the VPS certificate and refuses a mismatch **before** sending the token | Closes the interception hole on the trade-forwarding link |
| **015** | Bare-direction messages log once instead of once a second | 8,319 lines from one message becomes 1 |
| **017** | Backtests scored every timed-out trade as break-even | **Your backtest numbers will get worse, and they should** |

**017 is the one to read.** A backtested trade still open when it ran out of
bars was closed at the *entry* price, so it scored break-even wherever the
market had actually gone — in seven of the eight simulators. The eighth always
did it correctly, which is how it stands out as a bug rather than a choice.

The bias ran one way: a strategy that holds losers and drifts looked
break-even instead of losing. Nothing about live trading changed (the only
consumer is the Backtest page you drive by hand — I checked it does not feed
automatic strategy selection), but **if you chose a strategy partly on
backtested numbers, re-run it.**

All four were written test-first and mutation-tested. `tools.checks all` is
8/8 and the suite is 4,130.

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

**3. [bugs/016](../todo/bugs/016-phantom-open-trade-consumes-a-trade-slot.md) —
a trade that does not exist is holding one of your five trade slots.** Row
`83aa3510`, `status=open`, `mt5_ticket=0`, open since **2026-08-27 17:45**. The
broker has no positions and zero margin. The max-open-trades gate is a plain
count of open rows and never asks the broker, so with `max_open_trades = 5` this
ghost has been costing you **a fifth of your trading capacity for over a day**,
with nothing on screen to say so.

There is already a repair module for this class of row; its rule is to leave a
placeholder alone when it has no matching broker deal, on the grounds its legs
might still be resting. That rule has no age limit. Fixing it means giving it
one, and the threshold is your call — long enough not to kill a genuine resting
limit order, short enough not to lose a slot for a day. It is the close path, so
it needs a test first and a demo session.

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

## bugs/013 moved forward

Step 1 of 013 (does the EA stall still happen on the recompiled build?) is done:
**no recurrence since 16:05**, the minute the new build went in — 3.7 hours
clean. Suggestive, not proof.

It also turned out that **40 of the 76 warnings were the phantom trade above**,
not a live position. So more than half of 013's evidence was a trade that was
never at the broker. The eight-second stall during the M1 demo is still real.

## Note

The running app still has the pre-fix code loaded, so the bugs/015 log spam
continues until it is restarted.
