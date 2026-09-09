# 037 — Global Harvest threshold changed itself from $50 to $75

**Status:** OPEN, cause not found. Observed 2026-09-09 during the demo session.
**Money:** yes, indirectly. It is the number at which every open position on
the symbol is closed at once.

## What was observed

Verified at **16:02:28**, in the database and in the EA's own log:

```
[EABridge] global config updated: harvest_enabled=true harvest_threshold=50.0
```

Verified again at **16:22:24**, without anyone setting it:

```
[EABridge] global config updated: harvest_enabled=true harvest_threshold=75.0
```

Restored to 50 and confirmed in both the database and the EA.

## Why 75 is the interesting part

**75 is the value in `forex_trader_demo.db`** — the pre-migration database this
app no longer trades from. That file also holds `max_open_trades = 3`, which is
the number the owner queried on 2026-09-04 (*"the max open trades in the risk
settings is set to 3, why has it opened more trades?"*).

| database | harvest | max_open_trades |
|---|---|---|
| `forex_trader_demo.db` (old) | **75.0** | 3 |
| `forex_trader_demo_26004592.db` (live) | 50.0 | 5 |

## Ruled out, by checking rather than by reasoning

* **Schema default** — `global_harvest_threshold_usd REAL NOT NULL DEFAULT 50.0`.
  A default-fill on a partial upsert would produce 50, not 75.
* **The UI widget's default** — `rs.get("global_harvest_threshold_usd", 50.0)`.
  Also 50.
* **A per-template Harvest field** — the runbook warns these two settings share
  a name. No template on the account has 75: the governing one
  (`30 TP1 SL50 and Trail`) has `harvest_threshold = 0.0`.
* **Inbound cluster sync from the Mac.** `global_harvest_threshold_usd` IS in
  `_SYNCED_SETTINGS_KEYS`, and a Mac (192.168.3.230) was connected throughout.
  But `_handle_settings_propose` logs `[SyncServer] applied settings from Mac`
  on every accepted proposal, and **no such line exists in any of the session's
  three logs.** This was the leading hypothesis and it is wrong.
* **The startup database resolution.** `run.py` logs
  `could not resolve the per-account database — falling back to` on failure.
  No such line. bugs/031's fix is holding.

## What is left

Only one code path writes this column from the UI
(`_strategy_cards._save_global_params`), and it takes the value from the
Global Parameters widget. For it to write 75, that widget must have been
holding 75 — which means it was rendered from a source carrying the old
account's settings.

**Not yet explained, and deliberately not guessed at.** The next occurrence is
what will settle it.

## What to do when it recurs

1. Note the exact time and compare against the EA log's
   `global config updated` lines, which timestamp every change that reaches
   the EA.
2. Check `forex_trader_demo.db` for the value that appeared.
3. Check for `[SyncServer] applied settings from Mac` around that time.
4. Note whether the browser tab had been open across an app restart — that is
   the condition present here, and the one that could not be ruled out.

## Related

* [031](031-the-app-trades-one-account-and-books-to-another.md) — the same
  old-versus-new database confusion, in the trade ledger. Fixed; this is not a
  regression of it, since the fallback path did not fire.
* [handover/025](../../simon-handover/025-harvest-needs-the-ea-attached.md) —
  the EA holds this setting in memory only, so the EA log is the reliable
  record of what was actually in force.
