# 010 — A LIMITS message rests, whatever strategy the channel is on

**Status:** not started
**Depends on:** none
**Real-money surface:** yes — it changes which broker call a live signal makes. Needs owner sign-off before implementation and a demo session before it is trusted.
**Leverage:** the resting path already exists in full; this only stops routing around it.

## Problem

`backend/src/services/signals/scan_messages.py:390`:

```python
if parsed.get("tp_open") is not None and not _ea_templates.is_template_override(strategy):
    strategy = STRATEGY_LIMIT_RUNNER
```

`tp_open` is set only by `parse_limit_order_signal`, so its presence *is* the parser saying "this
message named limits". The second clause then throws that away whenever the channel has an EA
Template assigned.

For a **grid** template that is right — a grid stages its own resting legs, and the guard was added
on 2026-07-24 precisely so a configured grid actually ran. For a **single**-mode template it is
wrong, and there is no resting path behind it: `scan_auto_execute.py:444` stages a pending order only
when `mode == "grid"`. The signal falls through to the market branch, and IME's gap-fire
(`scan_auto_execute.py:508`) then fills it up to 15 points outside its own zone.

Live, 2026-09-10, GOLD DIGGERS INSTITUTIONAL, `Template: GD Instituational - single`: BUY zone
4410.00–4415.00 filled at 4428.76, gap +13.74, SL and all three TPs shifted up to match.

## Decision

Narrow the guard from "any template" to "a grid template". A limit-shaped message on a single-mode
template routes to `handle_limit_order_signal` and rests. Grid and non-template behaviour is
unchanged.

Rejected: suppressing gap-fire when `tp_open` is set. It would stop the bad fill but still leave the
signal queued for a Python-side zone re-entry rather than a genuine broker order, which is not what
a limit order is.

## Tests first (TDD)

- `tests/core/test_limit_keyword_beats_template.py`
  - a `tp_open` signal on a **single**-mode template channel calls `handle_limit_order_signal` and
    never `execute_auto_signal`
  - a `tp_open` signal on a **grid** template channel still calls `execute_auto_signal` (grid keeps
    its own placement branch)
  - a `tp_open` signal on a channel with no override is unchanged — still Limit Runner
  - a signal **without** `tp_open` on a single template still calls `execute_auto_signal`, so the
    market path is untouched
  - the gap-fire regression: a single-template `tp_open` BUY whose market price is 13.74 above the
    zone places a resting order and does **not** open a market trade
- Read the dispatch function's own source, strip comments and docstrings, and match `name(` — not a
  module-wide grep. Two tests in
  [reversal-engine/100](../reversal-engine/100-revalidating-every-waiting-order.md) passed with the
  guard deleted because they matched the `import` line.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. In `scan_messages.py`, replace the `is_template_override(strategy)` clause with a grid-only test.
   Put the "is this a grid template" question in one named helper — `ea_templates` is the right home
   — and call it from here and from `scan_auto_execute.py:444`, so the two cannot drift.
3. Update the comment block above the guard: it currently explains why templates win, which will no
   longer be the whole truth.
4. Record the constraint in `docs/system/domains/` for the signals domain.

## Where

- `backend/src/services/signals/scan_messages.py:373-396` — the guard and its comment
- `backend/src/services/broker/ea_templates.py` — the shared `is_grid_template(strategy)` helper
- `backend/src/services/trading/scan_auto_execute.py:441-445` — call the shared helper

## Acceptance

- A `[LIMITS]`-shaped message on a single-mode template channel results in a `place_pending_order`
  call and no `open_trade` call.
- Grid templates, non-template channels, and non-limit messages are byte-for-byte unchanged in
  behaviour.
- **The killer test:** replay the 2026-09-10 signal — BUY 4410/4415, market 4428.74, single template
  — and assert a resting BuyLimit at 4415.00, not a market fill at 4428.76.

## Notes

010 alone is an improvement (the order rests instead of chasing) but the fill is then managed by
`_resolve_management`'s fallback, not by the template. 020 and 030 are what make the template apply.
Do not demo 010 in isolation and call the feature done.
