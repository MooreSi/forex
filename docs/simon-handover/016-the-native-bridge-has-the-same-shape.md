# 016 — the native bridge may have the same hole, and I could not check

**Decision needed:** whether the native bridge is in use, and whether to fix it blind
**Money:** yes — it is an order-send path
**Urgency:** only matters if `mt5_native_bridge_enabled` is on

## What I found and fixed

The app talks to MetaTrader through one of two clients:

- **`mt5_client.py`** — over HTTP to the bridge program. This is the usual one.
- **`mt5_native.py`** — in-process, when `mt5_native_bridge_enabled` is set.

On 2026-08-31 I found that the HTTP one could not tell "the broker said no"
from "we never heard back". A read timeout — where the request reached the
bridge, the order may have filled, and only the reply was lost — came back
looking like a rejection, so the signal was put back in the queue and sent
again. That is the failure stage3/020 exists to prevent, on a route it had not
covered. Fixed, with tests.

## What I did not fix, and why

`mt5_native.py` has the same shape: `except Exception: return {"error": ...}`
on all four send paths.

I have not changed it. The HTTP case is decidable — httpx tells you whether the
request ever left the machine, so "retry safely" and "we do not know" can be
told apart precisely. The native client's failures come out of a thread
executor talking to the MetaTrader5 Python package directly, and I cannot tell
from reading it which of those mean the call never ran.

Guessing here is not safe in either direction:

- Treat everything as unknown → signals park whenever the native bridge
  hiccups, and only reconciliation releases them.
- Treat everything as retryable → the original bug, on the native path.

## What I need from you

1. **Is the native bridge actually in use on any install?** If it is off
   everywhere, this is documentation rather than a fix, and can wait.
2. If it is in use, it needs one demo-session experiment: stall the native
   bridge mid-send and see what exception comes back. Ten minutes at the
   terminal answers it properly, and then the fix is the same three lines as
   the HTTP one.

Until then the HTTP path — the one your installs actually use — is fixed, and
the native path is no worse than it was.
