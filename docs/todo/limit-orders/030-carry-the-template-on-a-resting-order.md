# 030 — A resting order carries its template (needs an EA recompile)

**Status:** not started
**Depends on:** [020](020-the-template-manages-the-fill.md) — same demo session
**Real-money surface:** yes — it changes how a filled position is managed at the broker. Owner sign-off before implementation; demo before trusted. **Also needs an EA recompile and a redeploy to MT5.**
**Leverage:** the `PendingOrder` struct already holds every field; the grid path already populates them.

## Problem

`place_pending_order` (`backend/src/services/broker/ea_bridge/__init__.py:464`) has no `template`
parameter. `open_trade` does — it forwards every template field generically as `tpl_<key>` at
`__init__.py:406-425` — but the pending path never did, because until 010 no template could ever
take it.

On the EA side, `HandlePlacePendingOrder` hardcodes the refusal
(`mql5/ForexTraderBridge.mq5:1335`):

```cpp
// This is the Limit Runner / ORB pending-order path, never a template --
p.isTemplate = false;
p.tplGridGroup = -1;
```

The good news is that this is **populating fields that already exist**, not adding any. The
`PendingOrder` struct at `mql5/ForexTraderBridge.mq5:300-333` already carries `isTemplate`,
`tplTpslMode`, `tplAnchor`, `tplTrailMode`, `tplBeMode`, `tplBeBufferPts`, `tplBeTrigger`,
`tplCancelPending`, `tplGroupTpAction`, `tplHarvestEnabled`, `tplHarvestThreshold`, `tplOrigSlDist`
and the raw `tplCfg` — because `HandleOpenTemplateGrid` fills them in per grid leg, and
`CheckPendingOrders()` already promotes a filled `PendingOrder` into a complete `ManagedTrade`.

## Decision

Extend `place_pending_order` with the same generic `tpl_<key>` forwarding loop `open_trade` uses, and
have `HandlePlacePendingOrder` read those fields the way `HandleOpenTemplateGrid` already does.
Generic forwarding, not a field list: `open_trade`'s own comment explains that a per-field mapping
meant every new template setting needed edits in three places.

`HandleRestorePendingOrder` needs the same treatment. It re-populates `g_pending[]` after an EA
restart from Python's durable `vantage_pending_orders` rows, and without the template fields an EA
recompile or terminal restart would silently demote a resting template order to an untemplated one —
the failure would appear only at fill, possibly hours later.

## Tests first (TDD)

Python side:

- `tests/core/test_place_pending_order_carries_template.py`
  - `place_pending_order(..., template={...})` emits one `tpl_<key>` per template key, and the values
    survive the JSON encoding the EA's minimal parser expects (booleans as `0`/`1`, per the
    `be_at_pos` / `close_full_on_last` precedent)
  - `template=None` emits **no** `tpl_*` keys at all — the existing Limit Runner / ORB payload is
    byte-identical to today
  - the restore path re-sends the same `tpl_*` fields for a still-working template row

MQL5 side — there is no MQL5 test runner in this repo, so this is verified by reading and by the
demo session. State that plainly rather than implying coverage. What to check by hand:

- a resting template order that fills is promoted into `g_trades[]` with `isTemplate = true` and
  every `tpl_*` value intact
- a recompile mid-rest, then a fill, produces the same result via `restore_pending_order`

## What to do

1. Write the Python tests above; run them; confirm they fail for the right reason.
2. `place_pending_order`: add `template: Optional[dict] = None` and the generic forwarding loop
   lifted from `open_trade`. Extract the loop so there is one copy.
3. The `hello` restore path in `ea_bridge/_dispatch`: include the stored template on each
   `restore_pending_order`. Check whether `vantage_pending_orders` already stores enough to rebuild
   it — it stores `strategy`, which is `template:<name>`, so the template can be re-fetched by name
   rather than duplicated into the table. Prefer that; a copy of a template in a second table is a
   copy that goes stale when the user edits the template.
4. MQL5 `HandlePlacePendingOrder`: set `isTemplate` from the `strategy` prefix, populate the `tpl_*`
   fields and `tplCfg` exactly as `HandleOpenTemplateGrid` does, keep `tplGridGroup = -1` (a single
   template order has no siblings).
5. MQL5 `HandleRestorePendingOrder`: same fields.
6. Recompile the EA. **The redeploy to MT5 is the owner's, not the session's.**

## Where

- `backend/src/services/broker/ea_bridge/__init__.py:352-425` — `open_trade`'s forwarding loop, to extract
- `backend/src/services/broker/ea_bridge/__init__.py:464-520` — `place_pending_order`
- `mql5/ForexTraderBridge.mq5:1283-1346` — `HandlePlacePendingOrder`
- `mql5/ForexTraderBridge.mq5:1348+` — `HandleRestorePendingOrder`

## Acceptance

- A resting order placed for a template channel fills and is managed by that template's rules — the
  same rules the same template applies to a market fill.
- A non-template resting order's wire payload is unchanged.
- **The killer test:** on demo, place a template limit order, recompile the EA while it rests, let it
  fill, and confirm the template's breakeven and trail still fire.

## Notes

Check the stale-EA-build guard before demoing: `template_blocked_by_stale_build`
(`ea_bridge/__init__.py:700`) exists because a template sent to an old EA build is silently
mismanaged, which is [bugs/033](../bugs/033-a-stale-ea-build-was-invisible.md). This change makes the
pending path a second way to hit that, so it needs the same guard.
