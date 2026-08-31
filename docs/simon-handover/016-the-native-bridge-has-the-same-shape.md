# 016 — the native MT5 bridge: answered, and I had it backwards

**Status:** fixed 2026-08-31. No decision needed from you any more.
**Money:** yes — it is an order-send path
**Correction:** the first version of this note said the native bridge probably
was not the one your installs use. That was wrong, and wrong in the direction
that mattered.

## Your question: if we're only using the Expert Advisor, do we need the bridge?

**Yes.** The bridge is not the order route — it is the connection to
MetaTrader. Even with the EA placing and managing every trade, the app has no
other source of:

| | Used by |
|---|---|
| **Prices** (`get_tick`) | the monitor loop, every stop and target check |
| **Candles** | every signal generator, every backtest |
| **Account** (balance, equity) | position sizing, the daily-loss and drawdown halts |
| **Open positions** | reconciliation, and the duplicate-order check |
| **Deal history** | reconciliation's evidence that a trade actually closed |

Roughly 97 places across ten areas of the app read one of those. Turn the
bridge off and the EA would keep managing whatever it already holds, while the
app went blind: no new signals, no risk figures, no reconciliation.

What the EA changes is **which code places and manages orders**, not whether
the app needs a connection. And it only covers strategies it can run — EA
Templates plus the portable list. Anything else, and any time the EA is
unhealthy or the handoff fails, falls through to the bridge's own send path.

## Where I had it backwards

There are two bridges, and I assumed the wrong one was in use:

- **`NativeMT5Bridge`** — imports MetaTrader5 directly, in-process. **This is
  the default on Windows**, and `run.py` explicitly skips launching the
  separate bridge program when it is on.
- **`MT5BridgeClient`** — talks HTTP to `mt5_bridge.py` as a subprocess. This
  is the **macOS** path, where MT5 runs under Wine and the app's own Python
  cannot import MetaTrader5 at all.

So on your Windows machine it is the native one. My first note said the HTTP
path was "the one your installs actually use", and fixed that one first. That
was the wrong way round.

## Now fixed, and the reasoning is stronger here

I had said I could not tell which native failures meant "the call never ran".
Reading it properly, I can — and the timeout case is clearer than the HTTP one.

`_call` runs the MetaTrader5 function as
`asyncio.wait_for(asyncio.to_thread(fn, ...))`. `wait_for` cancels the *wait*.
**It cannot stop the thread.** After the timeout fires, the MT5 call is still
running to completion. So a timeout on `place_order` does not mean the order
failed — it means the order is very likely still on its way to the broker,
and we stopped listening.

That is exactly the case where retrying produces two live orders, and until
today it came back looking like a plain rejection.

The one failure that provably never ran is a missing function name — `getattr`
raises before anything is dispatched — so that stays retryable. Parking a
signal over a plain programming error would be a second bug, not caution.

18 tests, three mutations, all caught, covering over-parking as well as
under-parking.

## What this means for your demo session

Nothing changes in the runbook. It does mean **demo 2 is now testing the path
your machine actually uses** — pull the connection mid-send and confirm the
signal shows `unknown` rather than `pending`. Before today that demo would have
exercised the fixed code on macOS and the unfixed code on Windows.
