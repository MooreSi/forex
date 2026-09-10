# 020 — The template manages the fill

**Status:** **BUILT 2026-09-10**, owner-signed-off, tests-first. `python -m tools.checks all` green. **NOT DEMOED** — no broker has seen any of it.
**Depends on:** [010](010-limit-keywords-beat-the-template.md); must ship in the same demo session as [030](030-carry-the-template-on-a-resting-order.md)
**Real-money surface:** yes — it sets the stop distance and the lot size on a live resting order. Owner sign-off before implementation; demo before trusted.
**Leverage:** every piece of template resolution already exists on the market path; none of it is reachable from the limit path.

## Problem

`_resolve_management` (`backend/src/services/trading/limit_order_signal.py:100`) explicitly refuses a
template:

```python
if is_template_override(override):
    # Should be unreachable -- engine.py routes template channels away
    # from this module entirely -- but a template's settings live in a
    # different shape altogether, so never try to ladder one here.
    return default
```

After 010 that branch is reachable and the comment is false. Left as-is, a limit signal on a
template channel rests and then fills under Limit Runner's own even-split ladder and the generic
`risk_per_trade_pct` sizing — the exact mismatch [bugs/023](../bugs/023-ime-template-sl-ignores-templates-own-stop.md)
found on the IME path, where a template's `sl_pips` was silently ignored in favour of a generic
placeholder stop.

Three things have to come from the template instead:

| | today on the limit path | should be |
|---|---|---|
| stop loss | the signal's own `stop_loss` | `sl_pips` (or `use_dynamic_atr` × `atr_sl_mult`) |
| TP ladder | signal TPs, split evenly by `_limit_runner_pcts` | `resolve_template_tps` |
| lot size | `risk_per_trade_pct` | template `risk_pct`, else `lot_anchor` capped at `max_lot_size` |

## Decision

`_resolve_management` returns the template, and `handle_limit_order_signal` resolves SL, TPs and lot
from it — reusing `resolution.py:540-576` for the stop, `open_trade.resolve_template_tps` for the
ladder and `scan_auto_execute.py:394-410`'s sizing shape. No second implementation of any of them.

**The price reference is the resting price, not the tick** (owner, 2026-09-10, QUESTIONS #1). `resolution.py` measures a template's SL
from `tick.ask`/`tick.bid` because a market order fills there. A resting order fills at the price we
are about to name, which may be an hour and many points away, so `sl_pips` must be measured from the
limit price or the stop distance is right and the stop level is wrong. This is the one place this
task cannot simply call the existing function — the conversion is shared, the reference is not.

## Tests first (TDD)

**Written 2026-09-10, red before any fix:**
[`tests/core/test_limit_order_template_management.py`](../../../tests/core/test_limit_order_template_management.py)
— 16 tests, **11 red, 5 green**. Unit-level against `handle_limit_order_signal` with a fake EA that
records its arguments; the routing that gets a signal here is 010's business, not this file's.

**Every test places the tick deliberately far from the resting price** — zone 4410–4415 with the
market at 4428.74, the live geometry. A tick-referenced implementation cannot pass any of them by
accident. `sl_pips = 60` from the resting price is 4409.00; from the tick it is 4422.74, which for a
BUY is seven points *above* the entry and not a stop at all.

The template's TP pips are 40 / 90 / 150, chosen so the expected ladder (4419 / 4424 / 4430) collides
neither with the signal's own stated 4418 / 4422 / 4427 nor with the tick-referenced 4432.74 /
4437.74 / 4443.74. A test that could pass while the template was ignored would be worthless here.

Red — the stop from `sl_pips` and measured from the resting price (both directions), the ladder from
the template's pips and measured from the resting price, `risk_pct` sizing, sizing against the
template's own stop, `lot_anchor` and its `max_lot_size` cap, the order stamped with the template
strategy, and the template dict reaching the wire.

Green, and must stay green — `sl_pips = 0` still defers to the signal's own stop, `tp_from_telegram`
still keeps the message's levels, a `TP OPEN` line still reserves the runner, an untemplated channel
is untouched, and the order still rests at the near edge. **All five verified capable of failing** by
breaking each assertion once and re-running.

One thing the fake had to get right: `suggest_lot_size_fn` returns 0.07 — neither the `lot_anchor`
(0.02) nor the `max_lot_size` cap (0.10). Returning either would have made both anchor tests pass on
the fake's own return value.

## What to do

1. ~~Write the tests above; run them; confirm they fail for the right reason.~~ Done 2026-09-10.
2. Extract the template-SL conversion out of `resolution.py:540-576` into one function that takes an
   explicit price reference, and call it from both sites. Do not copy it.
3. `_resolve_management`: return the template override for a single-mode template; keep the existing
   bail for grid (grid never reaches this module).
4. `handle_limit_order_signal`: when the management strategy is a template, resolve SL, TPs and lot
   from it before `place_pending_order`, and pass the template dict through (030 carries it).
5. Check the LOC ratchet before adding to `limit_order_signal.py` — 400 lines today. If it is
   baselined in `structure_baseline.json`, put the template resolution in a new module and add its
   `orphan_module_allowlist.json` entry in the same change.

## Where

- `backend/src/services/trading/limit_order_signal.py:100-165` — `_resolve_management`
- `backend/src/services/trading/limit_order_signal.py:257-300` — sizing and the `place_pending_order` call
- `backend/src/services/signals/resolution.py:540-576` — the SL conversion to extract
- `backend/src/services/trading/open_trade.py:130` — `resolve_template_tps`, called not copied

## Acceptance

- A resting order placed for a template channel carries the template's stop distance, its TP ladder
  and its sizing, and the values are identical to what the same template would produce on a market
  fill at the same price.
- `sl_pips = 0` and non-template channels are unchanged.
- **The killer test:** a template with `sl_pips = 60` and a BUY limit resting at 4415.00 places its
  stop at 4409.00 — while the tick sits at 4428.74, where a tick-referenced implementation would
  have put it at 4422.74.

## Notes

Until 030 ships, the template reaches the broker order but not the EA's management of the fill: the
`tpl_*` fields are dropped on the `place_pending_order` wire. Do not demo 020 without 030.
