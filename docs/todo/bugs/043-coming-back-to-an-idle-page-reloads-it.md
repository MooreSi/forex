# 043 — Coming back to an idle page reloads it, and that stalls the loop

**Status:** FIXED 2026-09-10, test-first. **Needs the owner to confirm the
symptom is gone**, since it depends on real browser throttling.
**Money:** no, but the reload costs a ~2s event-loop freeze, and the EA
reconnects after ten seconds of Python silence.
**Reported by the owner:** *"often if I haven't been using the app for a while
and come back to the web page it reloads."*

## Two layers, and the tighter one decides

`run.py` had already been tuned for this, with a comment naming background-tab
throttling as the cause. It tuned **uvicorn's** websocket ping:

```python
ws_ping_interval=30
ws_ping_timeout=60      # allow 60 s for a pong before closing
```

But NiceGUI's transport is socket.io, and `nicegui.nicegui` derives engine.io's
own deadline from a *different* parameter:

```python
sio.eio.ping_interval = max(reconnect_timeout * 0.8, 4)
sio.eio.ping_timeout  = max(reconnect_timeout * 0.4, 2)
```

| layer | pong window at the old settings |
|---|---|
| uvicorn `ws_ping_timeout` | 60 s, deliberately chosen |
| engine.io, from `reconnect_timeout=30` | **12 s** |

**The 60 s never applied.** A backgrounded tab is throttled by the browser to a
timer of roughly a minute or worse, misses a 12-second deadline, and engine.io
drops the session. The client reconnects and NiceGUI rebuilds the page.

## Why the rebuild is the expensive part

Every panel refreshes in one tick, each with its own database reads and bridge
calls, all on the event loop — measured at **2,065 ms** on 2026-09-10 06:36,
which is the owner opening the page. See
[030](030-the-apps-own-event-loop-stalls-are-unexplained.md), cause 3. Between
03:30 and 06:35, with nobody looking at the page, there were **no stalls at
all**.

## Fixed

`reconnect_timeout=150`, which makes engine.io's window **60 s** — the same
number already chosen for uvicorn beside it. The two layers now agree instead
of one silently overriding the other.

**The cost, stated plainly:** `reconnect_timeout` also governs how long the
server keeps a client's state after a real disconnect, and how long before the
"Connection lost" overlay appears. A genuinely closed tab now lingers about
2.5 minutes in server memory. On a single-user desktop app that is nothing; it
would matter on something with many clients.

`tests/frontend/test_socketio_and_uvicorn_timeouts_agree.py` pins the two
layers to agree rather than pinning 150 specifically — lowering
`ws_ping_timeout` is fine, engine.io silently deciding is not. It also asserts
NiceGUI still derives these from `reconnect_timeout`, so the arithmetic here
cannot quietly stop being true.

## Not fixed, and worth doing separately

The rebuild itself. ~25 render functions firing in one tick is the real cost,
and staggering them or moving their reads off the loop would help every
reconnect, not just this cause.
