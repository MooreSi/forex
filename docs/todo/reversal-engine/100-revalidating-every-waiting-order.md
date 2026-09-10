# 100 — Re-evaluating a waiting order before it becomes a trade

**Status:** **BUILT 2026-09-09.** The gap this file was raised for is closed;
what is left is listed at the bottom.
**Money:** yes — it refuses or holds trades that would otherwise open.
**Asked by the owner:** *"if there is a pending/resting order either in the app
or on the ea does it re-evaluate the order before executing the trade in case
the market has changed since the signal was created from either the reversal
engine or the telegram channels?"*

## The honest answer at the time: partly, and unevenly

There are **three** waiting states, not one, and they were being treated
differently:

| waiting state | what it re-checked when price arrived |
|---|---|
| Reversal Engine signal awaiting trigger | trading schedule, news blackout, fresh `ml_prob`, higher-timeframe bias, fill delay |
| EA resting order (`vantage_pending_orders`) | bias, swept every 60s and cancelled ([050](050-revalidate-resting-orders.md)) |
| **Telegram signal awaiting its zone** | **pre-trade filters only — and those are bypassed for every EA template** |

The Reversal Engine was thorough. The Telegram path was not: a signal could sit
queued for an hour, price could reach the zone **inside a news blackout or
outside the trading schedule**, and it would open regardless. On a
template-managed channel — which is most of them here — even the R:R and
directional-cap filters were bypassed, so effectively nothing was re-asked.

## What was added

`try_activate_pending_signals` now re-checks, before it opens anything:

* **the trading schedule**, `check_trading_schedule`
* **the news blackout**, `check_news_blackout`
* **the fill delay**, `governor.fill_too_soon` ([040](040-filter-the-instant-fills.md))

The same functions the Reversal Engine calls, not copies. A second
implementation of "are we in a blackout" is how two routes come to disagree,
which is the shape behind bugs/024, reversal-engine/080 and bugs/034.

**The bias is deliberately NOT re-checked here.** Activation runs through
`open_trade_from_signal` -> `resolve_open_trade_params`, where that gate
already sits outside the template exemption. Adding a second call would be the
duplication this file is arguing against.

## Proof

11 tests, red first. Five mutants killed — and **two survived a first pass for
the same reason**: the assertions searched the whole module, so they matched
the `from ... import check_trading_schedule` line and passed with the guard
deleted. Worse, because that import sits at the top of the file, it also
satisfied every "guard runs before the order" ordering check. The tests now
read the activation function's own source, strip comments and docstrings, and
search for `name(` so the call is distinguishable from the import.

## Still open

* **EA-side orders the app does not know about.** The 050 sweep reads
  `vantage_pending_orders`; an order placed on the terminal by hand is invisible
  to it. Out of scope for now, and worth stating rather than implying coverage.
* **Only the bias is re-checked on a resting order.** Schedule and news are not:
  a resting order is not cancelled because a blackout began. Arguably right —
  it may still fill after the blackout — but it is a choice, not an oversight.

  **Picked up 2026-09-10** by [limit-orders/040](../limit-orders/040-revalidate-before-the-fill.md),
  which widens the sweep to full parity with this path and withdraws (then re-arms) rather than
  holding.
* **None of this is demoed.** Four filters and three re-check paths now refuse
  or hold trades that previously opened.
