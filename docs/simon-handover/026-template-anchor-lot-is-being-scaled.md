# 026 — a fixed template lot of 0.10 is being traded at 0.13

**Decision needed:** yes. **Money:** yes — it is 30% more risk per trade than
you set.
**Found:** 2026-09-03, from ticket 1925815819.

## What happens

Five trades in the last seven days opened at **0.13 lots** against a template
whose Anchor Lot is **0.10**. Every one of them is on a `Telegram Auto (...)`
source:

```
Telegram Auto (Gold Diggers VIP)   signal lot 0.1  ->  trade 0.13
Telegram Auto (GOLD DIGGERS INST)  signal lot 0.1  ->  trade 0.10
```

Same signal size, different result. The difference is the channel's own lot
multiplier:

| channel | lot_mult | manual_override |
|---|---|---|
| `Telegram Auto (Gold Diggers VIP)` | **1.3** | 0 (set by the scorecard) |
| `Telegram Auto (GOLD DIGGERS INSTITUTIONAL)` | 1.0 | — |

0.10 x 1.3 = 0.13.

## Why the template's fixed lot did not protect it

`services/signals/resolution.py` already intends exactly this protection, and
says so:

> "A template's own fixed Anchor Lot (risk_pct == 0 branch above) is the same
> kind of deliberate manual value as lot_size_override -- scaling it silently
> (e.g. Reversal Engine's 1.3x -> 0.1 becoming 0.13) defeats the point of
> setting a fixed lot on the template."

The flag that carries that exemption, `_lot_is_template_fixed`, is set inside
this branch:

```python
lot_size = lot_size_override or sig.get("lot_size")
_lot_is_template_fixed = False
if not lot_size and _is_template and _template is not None:
    ...
    _lot_is_template_fixed = True        # only reached when lot_size was falsy
```

The Telegram Auto path stores a `lot_size` **on the signal itself** (0.1). So
`lot_size` is already truthy, the whole template branch is skipped, the flag
stays False — and the multiplier is applied a few lines later:

```python
if _ch_mult != 1.0 and not lot_size_override and not _lot_is_template_fixed:
    lot_size = lot_size * _ch_mult
```

The template IS fixed-anchor here (`risk_pct = 0.0`, `lot_anchor = 0.1`). The
exemption simply never engages, because a signal-carried lot arrives first.

Plain-channel trades on the same template are unaffected: their signals carry
no lot, so the template branch runs and the exemption holds. That is why it
looks occasional — 76 trades at 0.10 and 5 at 0.13 in the same week.

## Two ways to fix it, and they differ in meaning

1. **Set the flag whenever the resolved template is fixed-anchor**, regardless
   of where the lot came from. Smallest change, and it matches the comment's
   stated intent exactly.
2. **Let the template's Anchor Lot win over a signal-carried lot.** The same
   function says "a template's own Entries & Lots fields are authoritative for
   sizing", which argues the `not lot_size` guard is itself wrong. Bigger, and
   it changes sizing for any signal that carries its own lot.

I have not applied either. Both change the lot size on live trades, which
needs your sign-off and a demo session.

## What you can do right now, without any code change

The multiplier on `Telegram Auto (Gold Diggers VIP)` is **1.3 with
manual_override = 0**, meaning the scorecard computed it (17 samples, 58.8%
win rate) rather than you choosing it. Setting that channel's multiplier back
to 1.0 stops the scaling immediately.

Note the bare `Gold Diggers VIP` channel is also at 1.3 but with
`manual_override = 1` — that one you set deliberately, and it is working as
intended on its own signals.
