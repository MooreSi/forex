# 022 — Telegram approval succeeded and issued an empty licence key

**Status:** found and fixed 2026-09-02, from the owner's own machine.
**Touches money:** no. It touches whether anyone can start the app at all.
**Severity:** high. The failure mode is a button that reports success and does
nothing, which sends you looking everywhere except at the thing that broke.

## What the owner saw

> "restarted the app and got the telegram message, clicked 'perpetual', it
> didn't do anything except keep on presenting the same telegram message
> continually"

Approve was pressed. Telegram answered `Approved (Perpetual)`. The machine
stayed on the activation screen, re-registered on its next attempt, and the
same approval message arrived again.

## Why

There are **two** paths that put a machine into the pending queue: the
`MSG_REGISTER` branch and the sibling registration handler further down
`remote/server.py`. They build the same pending record, separately.

Only one of them stored `machine_id`.

```python
_reg = {"hostname": hostname, "platform": platform,
        "version": version, "email": msg.get("email", ""),
        "nickname": msg.get("nickname", ""), "ip": ip}   # <- no machine_id
```

`approve_registration` signs the licence *for the machine id*:

```python
machine_id = pending.get("machine_id", "")
if machine_id:
    if _kg_sign_fn:
        licence_key = _kg_sign_fn(machine_id, expiry_date)
```

With no machine id, the `if` is simply skipped. The token is approved, saved,
and un-revoked; `licence_key` stays `""`. Everything downstream is guarded on
truthiness, so all of it declines quietly:

- `if licence_key:` — no push to a connected client
- `if tok_meta.get("licence_key"):` — nothing sent on reconnect
- `if not (lic_key and machine_id): return` — no Licence Manager row

So the approval is real, the client is genuinely allowed, and it is never given
the thing it is waiting for. It reconnects, is still unlicensed, registers
again, and Telegram sends another request. That is the loop the owner was in.

This predates the current session's work: `git show HEAD~1` has the same
omission.

## The fix

Store `machine_id` in the `MSG_REGISTER` branch, as the other path already did.
One field.

## What was actually wrong underneath

Two paths to one place, only one of them complete. That is the third time this
exact shape has produced a defect here — see
[019](019-a-bad-ledger-row-drops-the-sync-link.md) and
[014](014-sync-and-licence-tls-are-unauthenticated.md).

The second failure is that **an approval with no key looked like success**. The
panel now says so:

```
⚠️ Licence key generation failed — check the signing key is registered.
```

## Tests

`tests/remote/test_registration_carries_the_machine_id.py` (11) pins the field
in both branches. `tests/remote/test_telegram_approval_end_to_end.py` (22) walks
the whole chain the owner described — button prefix to signed licence to the
console's Licence Manager to a reconnecting client collecting its key.

Every one was mutation-tested. Two findings worth keeping:

- The structural check on the register branch **passed with the field deleted**,
  because the word `machine_id` also appears in the comment explaining why the
  field is there. Comments are now stripped before the check. That is the third
  time a substring search has matched prose in this repo.
- The first `_auth_failures` mutation was aimed at the wrong one of two
  identical lines and reported a false survivor. The needle needs surrounding
  context; see `mutation-testing-wrong-target`.

## Reachability, checked rather than assumed

An earlier draft of this file claimed off-LAN clients could not reach the admin
server, on the grounds that `client.py` falls back to `SERVER_HOST`
(`217.155.25.160:8443`) while the server runs on the owner's Mac. That was
wrong: the owner confirmed the address IS that Mac, port-forwarded, and both
handshakes complete.

```
loopback   127.0.0.1        wss handshake: True
public IP  217.155.25.160   wss handshake: True
```

Note the limit of that evidence: the public-IP probe ran from inside the same
network, so it succeeds via hairpin NAT. It proves the forward exists and the
server answers on that address; it is not by itself proof that an outside host
is not blocked further upstream. The first real remote client settles that.

LAN clients find the server by UDP beacon or subnet scan; off-LAN clients use
the forwarded address. Both paths end at the same server, so approval behaves
identically either way.

## Still open

The Approve button only works while the bot command loop is running, and that
loop lives in `TradingRuntime.startup()` — so a machine that is the *first* to
register on a cold admin box still cannot be approved from Telegram. That is
[021](021-the-activation-screen-runs-with-nothing-started.md)'s open item and
needs the owner's decision, because a loop that can license machines before the
app is licensed is a security surface.
