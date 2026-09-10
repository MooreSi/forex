# 030 — A resting order carries its template (needs an EA recompile)

**Status:** **BUILT 2026-09-10**, owner-signed-off, tests-first. `python -m tools.checks all` green. **NOT DEMOED, and the EA must be redeployed and recompiled — EA_VERSION is now 1.07.**
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

**Written 2026-09-10, red before the fix:**
[`tests/core/test_place_pending_order_carries_template.py`](../../../tests/core/test_place_pending_order_carries_template.py)
— 9 tests. Six covering placement passed immediately, because 020 had already
added `place_pending_order(template=)` to get its own signed-off test green; the three covering the
**restore** path were red, which is the half this task actually added.

The wire tests subclass `EABridge` and record the message rather than mocking it, so the real method
bodies run — what goes on the wire is the entire question, and a mock would answer it with whatever
the test imagined.

Red, then green:

- the restore payload carries the template's `tpl_*` fields
- it carries the order's own resting `price`, which the payload never sent before — `ApplyTemplateToPending`
  anchors breakeven and the trail on it
- the template is read back **by name** at restore time, so an edited template restores under its
  current values

Green throughout, as controls: bools go out as `0`/`1` (a native Python bool evaluated false on the
EA side, which is how harvest and grid cancel-pending silently never fired — live 2026-07-23),
`name`/`created_at`/`updated_at` are dropped, a non-template order's payload carries no `tpl_` key at
all, and a template that has since been **deleted** still restores the order (losing the template is
bad; losing the order's tracking is the gap this method exists to close).

**The MQL5 half has no test runner in this repo.** Stated plainly rather than implied: nothing above
executes a line of MQL5, and the EA side is verified by reading and by the demo session. What was
checked mechanically: braces and parens balance exactly as they do at HEAD, and all **15** `tpl_*` /
`isTemplate` fields the `PendingOrder` struct declares are assigned by the new helper.

## What to do

1. ~~Write the Python tests above; run them; confirm they fail for the right reason.~~ Done 2026-09-10.
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

## What was actually built (2026-09-10)

One helper, two callers. `ApplyTemplateToPending(PendingOrder &p, const string &json, anchorPrice,
sl)` sits above `HandlePlacePendingOrder` and is called from both it and `HandleRestorePendingOrder`
— the same population from both, or a recompile mid-rest silently demotes a template order and the
difference shows only at the fill.

Nothing in the struct is new. `PendingOrder` has carried all 15 fields since the grid path was
written, and `CheckPendingOrders()` already copies every one into the `ManagedTrade` it promotes on a
fill. Only the hardcoded `p.isTemplate = false` stood in the way.

Three decisions worth keeping:

* **`anchorPrice` is the resting price**, not current market — a limit order opens where it rests, so
  that is what breakeven and the trail measure from. Same reasoning as Python's
  `template_levels.PriceRef`, which puts the order's SL and TPs there too.
* **`tplGridGroup` stays -1.** This is one order, not a leg with siblings, so nothing may cancel or
  group-close alongside it.
* **`closeFullOnLast` still comes from the explicit `close_full_on_last`**, not `tpl_close_full_on_last`.
  On this path that flag is the SIGNAL's — a literal "TP OPEN" line, which the grid path has no
  equivalent of — and the template must not overrule what the channel actually said.

`EA_VERSION` and `#property version` are both **1.07**, `EA_VERSION_DATE` 2026-09-10.

## Deploying it — the order matters

```bash
./tools/deploy_ea.sh
```

Then compile in MetaEditor (F7) and re-attach. The repo copy and MetaTrader's Experts copy are
unrelated files with nothing linking them; the script's own header records the day lost to
compiling a source three weeks old while every fix "was applied".

**Until that is done, every EA Template order is refused.** `template_blocked_by_stale_build` fires
whenever `ea_version_ok` is False, and it is False the moment the app ships 1.07 while the chart runs
1.06. That is the guard working as designed (bugs/033 — a template is managed entirely by the EA, so
a stale build runs it under replaced logic), but it means the version bump and the redeploy are one
operation, not two.
