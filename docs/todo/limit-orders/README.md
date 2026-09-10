# Limit orders — the keyword decides, not the template

**Status:** planning (pre-implementation)
**Domain:** limit-orders (Telegram limit-order path + the EA's resting orders)
**Created:** 2026-09-10

## 👋 Picking this up (agents start here)

1. **Read the plan** — this hub for the index + decisions; [QUESTIONS.md](QUESTIONS.md) for the
   decisions still open.
2. **Check [PROGRESS.md](PROGRESS.md)** — the shared status log. See what's done / in progress / free.
3. **Claim your task** in PROGRESS.md: set its row to `in progress`, add your name + date under Owner.
4. **Do the work** from the task file (`0N0-*.md` — tests-first + acceptance).
5. **Update PROGRESS.md** as you go — `done` (with commit) or `blocked` (say why).

Gates: tests first per the `/test` skill; **every task here touches order placement, so every task
needs explicit owner sign-off before implementation and a demo session before it is trusted**;
conventions per `backend-conventions`.

## What we're building & why

A channel message that says **"BUY LIMITS GOLD @ 4410/4415 AREA"** is asking for a resting order.
Today, if that channel has an EA Template assigned, the limit wording is thrown away and the signal
is executed at market instead — and because Immediate Market Entry then gap-fires anything within
15 points of the zone, it can be filled at a price the signal never named.

That is what happened on 2026-09-10: a BUY zone of 4410.00–4415.00 was filled at **4428.76**, 13.7
points above the top of its own zone, with SL and every TP shifted up to match. A limit order that
executes 13.7 points the wrong side of its entry is not the trade the channel sent.

The cause is two guards that each make sense alone. `scan_messages.py:390` gives an EA Template
priority over the format-triggered Limit Runner strategy — correct in 2026-07-24, when the point was
that a **grid** template must run its own resting legs. But a **single**-mode template is a
market-fill strategy, and there is no resting path behind it at all: `scan_auto_execute.py:444` only
stages a pending order when `mode == "grid"`. So a limit signal on a single template has nowhere to
rest, falls through to the market branch, and gap-fires.

The fix the owner asked for (2026-09-10): **the keyword decides the entry mechanic; the template
decides the management.** If the message says LIMITS, a resting BuyLimit/SellLimit goes on the book.
When it fills, the template applies its SL, its TP ladder, its breakeven/trail rules and its sizing,
exactly as it would on a market fill. Grid templates are untouched — they already rest.

And because a resting order can sit for up to an hour before it fills, it must be re-judged against
the market it is about to enter, not the one it was created in. Today only the higher-timeframe bias
is re-asked ([reversal-engine/050](../reversal-engine/050-revalidate-resting-orders.md)); the owner
wants full parity with what a queued Telegram signal already gets, and a Telegram message whenever an
order is withdrawn on that basis.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live shared status log |
| [QUESTIONS.md](QUESTIONS.md) | Decisions to confirm / answered |
| [010-limit-keywords-beat-the-template.md](010-limit-keywords-beat-the-template.md) | Route a LIMITS signal on a single-mode template to a resting order, not a market fill |
| [020-the-template-manages-the-fill.md](020-the-template-manages-the-fill.md) | Template SL / TP ladder / sizing applied to the resting order and its fill |
| [030-carry-the-template-on-a-resting-order.md](030-carry-the-template-on-a-resting-order.md) | `place_pending_order` and the EA carry `tpl_*` on a resting order (needs a recompile) |
| [040-revalidate-before-the-fill.md](040-revalidate-before-the-fill.md) | Widen the 60s resting sweep to the full gate set, proximity-triggered, and cancel on failure |
| [050-announce-a-discarded-limit-order.md](050-announce-a-discarded-limit-order.md) | Telegram alert naming the order and the gate that withdrew it |

## Decisions locked with the user (2026-09-10)

| Decision | Choice | Source |
|---|---|---|
| Keyword vs template precedence | The **keyword** decides the entry mechanic; the template decides the management. A LIMITS message rests, whatever strategy the channel is on. | user, 2026-09-10 |
| Grid templates | Unchanged. A grid template already stages resting legs across the zone, so it is already a limit order; routing it through Limit Runner would place one order where the user configured several. | this pack, from `scan_auto_execute.py:421-440` |
| Pack home | Own pack, cross-linked from [reversal-engine/100](../reversal-engine/100-revalidating-every-waiting-order.md) and [bugs/040](../bugs/040-a-resting-order-filling-into-news-is-not-closed.md), rather than extending the Reversal Engine pack. | interview, 2026-09-10 |
| Re-check breadth on a resting order | Full parity with the queued path: schedule, news blackout, fill delay, pre-trade filters, M5 momentum, plus the bias it already asks. | interview, 2026-09-10 |
| Proximity trigger | Re-check the full gate set once price is within **10 points** of the resting price; the cheap bias check keeps running every sweep. | interview, 2026-09-10 |
| A failed re-check | **Withdraw and re-arm.** The broker order is cancelled, but the setup stays alive until its original TTL expires and is re-placed if every gate passes again. | user, 2026-09-10 |
| Template stop reference on a resting order | Measured from the **resting price**, not the tick at placement — that is where the trade actually opens. | user, 2026-09-10 (QUESTIONS 1) |
| Toggle for the widened sweep | **Its own tunable**, default on. `htf_bias_gate_enabled` keeps governing only the bias half, so the trend gate and the news/schedule re-check switch independently. | user, 2026-09-10 (QUESTIONS 2) |
| Alert noise on a flap | Announce the **first** withdrawal and the **first** re-placement per signal, then stay quiet; report the flap count once in the final message. | user, 2026-09-10 (QUESTIONS 3) |

## Building blocks we reuse (do not rebuild)

| Need | Existing code |
|---|---|
| Place a genuine resting BuyLimit/SellLimit | `backend/src/services/trading/limit_order_signal.py:167` — `handle_limit_order_signal`, already the only path that does this |
| Decide who manages the fill | `backend/src/services/trading/limit_order_signal.py:100` — `_resolve_management`; today it bails on a template |
| Forward a template to the EA as flat `tpl_*` | `backend/src/services/broker/ea_bridge/__init__.py:406-425` — `open_trade`'s generic forwarding loop |
| Hold template fields on a resting order | `mql5/ForexTraderBridge.mq5:300` — `PendingOrder` already carries every `tpl_*` field, populated by the grid path |
| Template SL from `sl_pips` / `use_dynamic_atr` | `backend/src/services/signals/resolution.py:540-576` — the canonical conversion, `sl_pips * PIPS_TO_PRICE_XAUUSD` |
| Template TP ladder | `backend/src/services/trading/open_trade.py:130` — `resolve_template_tps` |
| Template sizing (`risk_pct` / `lot_anchor`) | `backend/src/services/trading/scan_auto_execute.py:394-410` |
| Sweep resting orders and cancel | `backend/src/services/trading/resting_revalidation.py:35` — `revalidate_resting_orders`, run every 60s from `positions/monitor_cycle.py:198` |
| The gate set to re-ask | `backend/src/services/signals/pending_activation.py:432-525` — schedule, news, `fill_too_soon`, pre-trade filters, M5 momentum |
| Withdraw an order at the broker | `ea.cancel_pending_order(trade_id, ticket, reason)` — `mql5/ForexTraderBridge.mq5:862` |
| Send a Telegram alert | `backend/src/services/telegram/alerts.py` — `send_message` + the `fmt_*` family |

## Out of scope

- **Grid templates.** Already resting; nothing in this pack changes them.
- **Orders placed by hand on the terminal.** The sweep reads `vantage_pending_orders` and cannot see
  them — stated in [reversal-engine/100](../reversal-engine/100-revalidating-every-waiting-order.md)
  and still true.
- **Closing a position that already filled into a news blackout.** That is
  [bugs/040](../bugs/040-a-resting-order-filling-into-news-is-not-closed.md), a separate owner
  decision about the *close* path, not the cancel path.
- **The 15-point gap-fire cap itself.** `MAX_GAP_FIRE_PTS` is not changed here. Once 010 lands, a
  LIMITS signal never reaches gap-fire; a non-LIMITS signal's behaviour is deliberately unaltered.

## Open questions

See [QUESTIONS.md](QUESTIONS.md). The short list:

- ~~Where is a resting order's template SL measured from?~~ (answered 2026-09-10: the resting price)
- ~~Which toggle turns the widened re-check on?~~ (answered 2026-09-10: its own tunable, default on)
- ~~How is a withdraw/re-arm flap damped on Telegram?~~ (answered 2026-09-10: first withdrawal and
  first re-placement, then quiet)
- **Open:** does the EA recompile go out with 030 alone, or is the whole pack demoed in one session?
