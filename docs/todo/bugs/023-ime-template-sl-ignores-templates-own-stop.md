# 023 — IME's template path ignores the template's own SL, and says "awaiting follow-up" for a follow-up that never comes

**Status:** built 2026-09-03, test-first, per the spec below — NOT VERIFIED
AGAINST A BROKER. Needs a demo session before this is trusted: a
template-managed channel's instant entry should place its SL at the
template's configured distance (or the ATR-clamped placeholder, for a
template that leaves `sl_pips` at 0), and the Telegram message should name
the template instead of promising a follow-up that will never arrive.
**Found:** live, 2026-09-03 — Gold Diggers VIP (template-managed channel) BUY at $4481.21, SL $4469.18 flagged "provisional 12.0 pts / -$120 max — awaiting follow-up".
**Touches money:** yes — the stop-loss distance placed with a real order, on the Immediate Signal Entry (IME) path.
**Severity:** every template-managed channel's instant entries get a stop that ignores the template's configured `sl_pips`/`atr_sl_mult`, silently, every time.

## What was seen

Gold Diggers VIP is mapped to an EA template ("Staged Ratchet 100-500" per the
2026-08 incident referenced in `instant_followup.py:62-63`). An instant BUY
fired, and the Telegram alert read:

```
Immediate Signal Entry (Gold Diggers VIP)
BUY at $4481.21 | lot 0.10 | ticket 1927668618
SL: $4469.18 (provisional 12.0 pts / -$120 max — awaiting follow-up)
```

The user expected the template's own SL config to apply immediately, the same
way the template's TP ladder does. Instead the order went out with a generic
ATR-clamped 8-25pt placeholder stop, and the message implied a follow-up
message would correct it later.

## Root cause

Two independent bugs, both in
[`backend/src/services/trading/instant_entry.py`](../../../backend/src/services/trading/instant_entry.py):

**1. The template branch never reads the template's own SL.**
Lines 226-247: when `_template_ime is not None`, the code computes the same
generic ATR-clamped provisional distance used by the *non-template* branches
right below it (248-307), instead of the template's `sl_pips` /
`use_dynamic_atr` + `atr_sl_mult`. The template is already fetched at
183-194 (`_template_ime`) but only consulted for Sig Guard and the Anchor
Lot — never for SL. The comment at 234-236 rationalizes this as "a
template's own sl_pips isn't in comparable point-from-fill terms for this
placeholder", but `resolution.py` (the non-instant signal path) solves
exactly that conversion at 547-562: `sl_pips * PIPS_TO_PRICE_XAUUSD`,
measured from the current tick, same reference `resolve_template_tps()` uses
for the TP ladder.

**2. The message always says "awaiting follow-up" for template trades.**
Line 331-337: `_ime_self_managed` only covers
`STRATEGY_CONSERVATIVE`/`STRATEGY_CONSERVATIVE_TRIAL`. Template-managed
trades fall through to the "provisional... awaiting follow-up" wording even
though [`instant_followup.py:57-77`](../../../backend/src/services/trading/instant_followup.py)
explicitly skips applying any follow-up SL/TP when `managed_by == "ea"` —
the EA manages SL/TP itself from the template config on-tick. So the message
promises a correction that structurally cannot happen.

## Why this is a bug, not intended behaviour

"Wait for a follow-up" is the right design for **non-template** channels,
whose signal generators don't reliably carry a usable stop up front. But once
a channel has a configured template, `resolution.py:527-536` already
establishes the policy for the equivalent non-instant path: *"A template's
own SL (sl_pips) is meant to be as authoritative as its TP ladder... This was
a no-op unconditionally"* — that was itself a prior bug fix. IME's template
branch was never given the matching fix.

This is also the same bug shape as the Anchor Lot fix already shipped on this
exact path (`instant_entry.py:203-214`, covered by
`test_template_uses_lot_anchor_not_hardcoded_001` and its three siblings in
`tests/core/test_instant_entry_surface.py:144-191`): a template field that's
supposed to be authoritative gets silently overwritten by generic sizing
logic on the IME path specifically, because IME duplicates `resolution.py`'s
logic instead of sharing it.

## What to change

In `instant_entry.py`, inside the `if _template_ime is not None:` branch
(226-247):

1. Compute `_tpl_sl_dist` the same way `resolution.py:547-556` does:
   - if `_template_ime.get("use_dynamic_atr")` and candle data is available,
     `compute_atr(...) * atr_sl_mult`;
   - else if `sl_pips > 0`, `sl_pips * PIPS_TO_PRICE_XAUUSD`;
   - else (sl_pips unset/0) fall back to the existing ATR-clamped provisional
     formula — unchanged behaviour for templates that genuinely don't set a
     stop.
2. Derive `provisional_sl` from `_tpl_sl_dist` (measured from `entry_px`,
   consistent with how the rest of the function already measures from
   `entry_px` rather than a fresh tick — templates fire at market so the two
   are effectively the same reference).
3. Recompute `_ime_max_loss` from whichever distance was actually used, so
   the Telegram message's dollar figure stays correct.
4. Extend the `_ime_self_managed` check (331-337) to also cover
   `_template_ime is not None`, and give template trades their own message
   variant — not "levels set by strategy immediately" (that phrasing is
   Conservative-specific) but something naming the template, e.g.
   `_(SL from template "{name}")_` — so the message stops promising a
   follow-up that `instant_followup.py` will never apply.

No change to `resolution.py`, `open_trade`, or anything on the close path.
This only touches how `instant_entry.py` computes the SL *distance* it
already passes to `open_trade(..., stop_loss=provisional_sl, ...)` — the
call itself, its signature, and everything downstream of it are untouched.

## What not to change

- Don't touch the non-template branches (248-307) — they're correct for
  channels with no template, and this bug doesn't affect them.
- Don't touch `instant_followup.py`'s `managed_by == "ea"` skip — that's
  correct and is the reason the message needs to change instead.
- Don't collapse this with the Anchor Lot fix's follow-up cleanup or any
  other tidy-up in the file. Smallest change: SL distance computation plus
  the message branch, nothing else.

## Test plan (write first, watch fail)

Model directly on the existing template-lot tests in
`tests/core/test_instant_entry_surface.py` (144-191), which cover this exact
shape of bug on this exact function. All fakes — `_FakeBridge`, `open_trade`
mocked via `mock.AsyncMock`, `fresh_db` fixture. No test may reach a real or
demo broker call; `open_trade` stays mocked so nothing downstream of the SL
number is exercised.

New cases, alongside the lot-anchor ones:

1. `test_template_sl_pips_used_not_generic_provisional` — template with
   `sl_pips=50, risk_pct=0`. Assert `open_trade.call_args.kwargs["stop_loss"]`
   equals `entry_px ∓ 50 * PIPS_TO_PRICE_XAUUSD` (direction-appropriate), not
   the 8-25pt ATR-clamped value.
2. `test_template_use_dynamic_atr_overrides_sl_pips` — template with
   `use_dynamic_atr=True, atr_sl_mult=1.5, sl_pips=50`, with `dpm_candles`
   patched/passed so `compute_atr` returns a known value. Assert the stop
   distance is `atr * 1.5`, not `50 * PIPS_TO_PRICE_XAUUSD`.
3. `test_template_sl_pips_zero_falls_back_to_provisional` — template with
   `sl_pips=0` (unset), no `use_dynamic_atr`. Assert the existing ATR-clamped
   8-25pt provisional logic still applies unchanged — this is the
   regression guard that the fallback path wasn't broken.
4. `test_template_ime_message_names_template_not_awaiting_followup` — patch
   `telegram_alerts.send_message` (already an `asyncio.create_task` fire, so
   patch the function itself) and assert the sent text does **not** contain
   "awaiting follow-up" for a template trade, and does contain the template
   name.

Each must be watched red against the current code before the fix lands —
1-3 should fail today because `stop_loss` currently equals the generic
ATR-clamped value regardless of `sl_pips`; 4 should fail today because the
message always says "awaiting follow-up" for template trades.

## Verification

```bash
pytest tests/core/test_instant_entry_surface.py -q
python -m tools.checks all
pytest tests/core/test_close_trade_characterization.py -q
git diff --stat tests/core/test_close_trade_characterization.py   # must be empty
```

## Sign-off needed

This changes the SL distance placed with a real order on the IME path for
every template-managed channel — squarely inside `open`
(`services/trading/instant_entry.py`) per
[docs/system/rules/20-trading-safety.md](../../system/rules/20-trading-safety.md).
Per that file: reading is free, changing needs owner sign-off and a demo
session before merge. The characterization/regression tests above can be
written and watched red/green without a broker, but the change itself should
not go live without that demo pass — a template that has been silently
getting the wrong stop distance for however long this has been happening
should be confirmed on a demo tick before every such channel's real stop
distance changes at once.
