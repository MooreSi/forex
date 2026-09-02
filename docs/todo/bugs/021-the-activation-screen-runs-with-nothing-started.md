# 021 — The activation screen runs with almost nothing started

**Status:** three consequences found and fixed 2026-09-02; the shape is worth
recording because a fourth is likely.
**Found:** the owner's Mac lost its licence file, restarted, and could not get
back in.
**Touches money:** no. It locks the owner out of the app entirely, which is
worse in a different way.

## The shape

`run.py` calls `guard.enforce()` before anything else starts, and on a missing
licence that shows the activation screen and **never returns**. So everything
that would normally be running — the database, the admin server, the Telegram
bot loop, the engines — simply does not exist on that screen.

The screen is not passive. It registers the machine, and on the admin machine
it must bring up the thing that can issue a licence. Each thing it needs turned
out to be missing, one at a time.

## Three consequences, in the order they appeared

**1. The admin server never started.** The screen started the remote *client*,
which dialled `217.155.25.160:8443` — this same Mac. The server is started from
`app.startup()`, which the guard never reached. `Connection refused`, for ever.
The machine that issues licences could not issue one to itself.
*Fixed: the activation screen starts the admin server when this is the admin
machine.*

**2. The database was never opened.** With the server up, the registration
arrived and then:

```
[RemoteServer] Registration Telegram notify failed: no such table: telegram_config
```

The alert was firing; it could not read the Telegram settings.
*Fixed: `run.py` opens the database before the licence check. The licence
DECISION does not move — the guard reads a file in the home directory — and the
engines still start only after it.*

**3. The Telegram bot loop never started.** The message sends over plain HTTPS,
so it arrived. The **button press** needs the bot to poll `getUpdates`, and
`_bot_command_loop` lives in `TradingRuntime.startup()`. Clicking Approve did
nothing.
***Not fixed.*** See below.

## Found alongside: 139 notifications in an hour

The client re-registers every 15 seconds, and the server announced it every
time — **139 Telegram messages in an hour for one pending machine**. Correct to
re-register (an admin who missed the first request must still be able to
approve after a restart); wrong to re-announce.

*Fixed: the pending entry is always refreshed so the console shows a current
timestamp, but the notification goes only when the details the admin acts on
have changed. Keyed by token, because the admin approves a token — the same
machine with a new one is news again.*

## What is left

**The Approve button in Telegram cannot work on the activation screen**, because
nothing is polling for it. Three ways out, none of them started:

1. **Run a minimal bot poll loop on the activation screen.** Correct, and the
   only option that makes the Telegram flow work as the owner expects. It means
   starting a Telegram poller in a process that is otherwise deliberately inert,
   and deciding what it is allowed to act on — approving a registration, and
   nothing else.
2. **Approve from the admin console instead.** It is running on that screen now
   (consequence 1's fix), so this works today. It is the designed admin path;
   Telegram is the convenience.
3. **Install a signed key directly** — `tools/generate_debug_licence --install`.
   What the owner did to get back in.

Option 1 is the real fix and wants a decision: a bot loop that can approve
machines, running before the app is licensed, is a security surface. It should
probably be restricted to registration callbacks only.

## The lesson

Every one of these was invisible until the exact moment it was needed, because
the activation screen is the one path nobody exercises. It is also the only way
back in when something goes wrong, which is precisely when it has to work.

Worth a test that boots the app with no licence and asserts the screen's own
dependencies are present, rather than finding the fourth one the same way.
