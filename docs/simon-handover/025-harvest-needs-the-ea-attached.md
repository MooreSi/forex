# 025 — Global harvest: armed and correct. My first report was wrong.

**Status:** investigated 2026-09-02, **corrected 2026-09-03** after the owner
said the EA was attached. He was right; I was wrong.
**Money:** yes — it closes live positions.

## The correction first

I reported "the EA is not attached", from this:

```
EA effective status : False
EA healthy          : False
secs since last seen: None
```

**That check was invalid.** `ea_is_healthy()` reads `_bridge.get_instance()` —
an in-process singleton. I ran it in a separate Python process, where no
bridge exists, so it returns False whatever the running app is doing. It said
nothing about your install.

The correct external check is the socket:

```
Python     13895  127.0.0.1:9111 (LISTEN)
terminal64 38762  127.0.0.1:54657->127.0.0.1:9111 (ESTABLISHED)
```

And the app's own log:

```
10:04:15 [EABridge] EA connected from ('127.0.0.1', 54657) on port 9111
10:04:15 [EABridge] EA hello: account=25470480 symbol=XAUUSD
10:04:15 [EABridge] EA v1.05 (compiled 2026.09.03 10:04:05, build 6140)
10:04:15 [EABridge] pushed 1 open position(s) back to the EA after reconnect
```

The EA is attached, current, and talking.

## Why nothing has been harvested

Nothing is wrong. The threshold has not been reached.

| | |
|---|---|
| `global_harvest_enabled` | `1` |
| `global_harvest_threshold_usd` | **$75.00** |
| open position | ticket 1924896615, XAUUSD, 0.10 lots |
| its profit right now | **$4.30** |

$4.30 against a $75 threshold. `CheckGlobalHarvest()` runs on every tick and
correctly does nothing. The EA's handler parses both fields and prints a
confirmation to the Experts tab:

```mql5
g_globalHarvestEnabled      = JsonGetLong(json, "harvest_enabled", 0) != 0;
g_globalHarvestThresholdUsd = JsonGetDouble(json, "harvest_threshold", 50.0);
Print("[EABridge] global config updated: harvest_enabled=", ...);
```

**If you want to confirm it armed on your side**, look in MT5's Experts tab for
that "global config updated" line at the time the EA connected. It should read
`harvest_enabled=true harvest_threshold=75.0`. I could not read that log from
here — the running terminal is the CrossOver prefix and its log directory is
not where the standalone MetaQuotes install keeps one.

## The one real limitation, unchanged

```mql5
if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
```

Harvest only sees positions on the EA's **own chart symbol**. With the EA on
XAUUSD, a EURUSD position is invisible to it. If you only trade XAUUSD this
never matters. If you do not, covering every symbol needs a Python-side
monitor that closes positions — money path, sign-off and a demo.

There is also still no Python-side fallback: basket harvest has one, global
harvest does not, so it fails completely rather than degrading if the EA ever
does drop.

## What to take from this

Nothing to fix for the case you reported. Lower the threshold, or wait for a
position to clear $75, and it will fire. The lesson on my side is that an
in-process singleton cannot be inspected from another process, and I should
have checked the socket first.
