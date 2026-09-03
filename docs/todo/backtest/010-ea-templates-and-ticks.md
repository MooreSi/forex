# Backtest: EA templates, and ticks

**Status:** scoped 2026-09-03, not started. **Owner decision needed before
phase 2.** **Money:** no — the backtest places no orders — but its numbers are
used to choose settings that do.

Item 7 of the owner's 2026-09-03 list: *"change this from strategies to EA
templates, also if new EA templates are created they should appear here
automatically. For historical price data are you able to add 'Ticks' into the
timeframe drop-down? is this supported?"*

These are two independent pieces of work. Ticks is the smaller one and is
worth doing first.

---

## Where the backtest is today

| | |
|---|---|
| `services/backtest/engine.py` | 526 lines — fills, dispatch, aggregation |
| `services/backtest/simulators.py` | 665 lines — **11 hand-written simulators** |
| `frontend/pages/backtest.py` | 614 lines — timeframe, days, strategy checkboxes |

Every simulator has the same shape:

```python
def _simulate_conservative(
    candles: list[dict], sig: BtSignal, fill_bar: int, fill_price: float,
    is_buy: bool, balance: float, risk_pct: float, fixed_lots: float = 0.0,
) -> BtTrade
```

Two things follow from that signature, and they are the whole scope:

* it walks **candles** — OHLC bars, not ticks;
* it is written **per built-in strategy**. There is no notion of an EA
  template anywhere in `services/backtest/`.

---

## Why "just add templates to the list" is not the job

An EA template is not a variant of a built-in strategy. It is a different
execution model:

* a built-in strategy is resolved by **Python** into concrete SL/TP prices
  before the EA sees the trade, and the simulators reimplement that resolution;
* a template is managed **by the EA, on every tick**, from its own 94 fields.

The management logic is `ManageTemplate()` in `ForexTraderBridge.mq5` — lines
2655 to 2941, **287 lines**, executed per tick. It covers the emergency-SL
backstop, breakeven modes and triggers, the partial-close ladder, anchor and
pending entries, grid legs and sibling cancellation, trail modes (candle,
points, TP-follow), and TP-cleared detection.

Simulating a template means reproducing that in Python.

**The risk is not the effort, it is the fidelity.** A template backtest that
diverges from what the EA actually does produces numbers that look
authoritative and are wrong, and they would be used to pick the templates that
trade real money. Divergence is silent: nothing compares the two.

---

## Phase 1 — Ticks (independent, worth doing on its own)

**Yes, MT5 supports it, and the bridge already uses it.** `mt5_bridge.py`'s
`_get_spread_at` calls `mt5.copy_ticks_from` today to find the real bid/ask
behind a historical fill.

### Measured, 2026-09-03

Probed with a standalone, read-only script run against the live Wine bottle
as a **separate process** — `mt5.initialize()` with no path argument attaches
to the terminal that is already running rather than launching a second one
(the same reasoning `mt5_bridge.py:142-147` documents), and the script never
called `mt5.login()`, so the live bridge's own session was never touched.
Deleted after the numbers were captured; nothing was left running or added to
the app.

| | |
|---|---|
| One closed hour, XAUUSD | **29,580–34,584 ticks, 1.7–2.0 MB** (`copy_ticks_range` numpy struct array, `.nbytes`) |
| Retention | **~93–95 days**, a hard cutoff — confirmed against five separate weekdays (25–29 May, all zero) so it is not a weekend gap; 2 Jun 2026 still returns data, 31 May does not |

A day is **not** "a few MB" — at this hourly rate a full trading day is
several hundred thousand ticks, tens of MB, over an HTTP bridge running under
Wine that already shows contention under concurrent calls (see the
`_mt5_call_lock` comment in `mt5_bridge.py:130-141`). A single day is
plausible; a multi-day or multi-week backtest window, pulled tick-by-tick
over HTTP, is not — that pull would dwarf the candle endpoints by two to
three orders of magnitude per day requested.

The 93–95 day retention window also bounds what "Ticks" could ever cover:
about a quarter's worth of history, not the months candles currently offer.

What is still missing:

1. **A history endpoint.** The bridge serves `/candles`, `/candles_range` and
   `/candles_symbol`. Tick history needs its own, backed by
   `copy_ticks_range`, and — given the volume above — should accept a bounded
   window (an hour or a day, not an open-ended range) rather than mirroring
   `/candles_range`'s shape.
2. **Simulators that walk ticks.** Each currently iterates bars. Either they
   take an abstracted price stream, or a tick feed is aggregated into
   pseudo-bars — which throws away the accuracy that motivates the change.

**Why it is worth it.** The M5 and M15 descriptions in the UI already admit
the flaw: when one bar spans both SL and TP1 the simulation *"assumes TP1 hit
first (optimistic)"*. On a scalping SL that is not a rounding error. Ticks
remove the ambiguity entirely — the sequence is observed rather than assumed.

**Deliverable:** a `Ticks` entry in the timeframe dropdown, with its own
max-days limit derived from the measured depth, and honest UI text about the
window it can cover.

---

## Phase 2 — EA templates in the backtest

Three options. **This is the decision I need.**

### A. Ship it only where it is faithful

Implement the template fields that map cleanly onto a bar/tick walk — fixed
anchor lot, SL, the TP ladder with partial closes, breakeven, the trail modes
— and **refuse to backtest a template that uses anything not implemented**,
naming the field. Grid entries and pending-leg management are the likely
exclusions.

Honest, testable, and the UI can say which templates are supported and why the
rest are not. Smallest correct thing.

### B. Full parity

Port all 287 lines. Highest fidelity, largest surface, and the maintenance
burden is permanent: every future EA change must be mirrored in Python or the
backtest silently drifts. **This needs a drift guard** — at minimum a test
that fails when `ManageTemplate` changes without the simulator changing, in
the spirit of the EA-version handshake that already exists.

### C. Replay instead of simulate

Do not reimplement anything. Feed historical ticks to the **real EA** in MT5's
own Strategy Tester and read the result back. Perfect fidelity by
construction; the cost is that it runs in MetaTrader, not in this app, and
wiring the result back into this UI is its own integration.

**My recommendation: A, then reassess.** It is the only one that cannot
produce a confidently wrong number, and it tells us from real use which
excluded fields anyone actually misses.

---

## Phase 3 — Templates appear automatically

Small once phase 2 exists. The picker currently renders `STRATEGY_NAMES`
checkboxes; it becomes a read of `list_ea_templates()`, the same source
Trading > Strategy already uses. Support status per template comes from
whichever option above is chosen.

---

## Status

Phase 2 (option A, refuse rather than approximate) and phase 3 (templates
listed automatically) shipped 2026-09-03. Phase 1's volume/depth probe is
done, above.

## What I need from you

1. **Whether ticks are still worth building, now that the cost is measured.**
   Tens of MB/day over the Wine HTTP bridge, and only ~93–95 days of history
   available at all — so "Ticks" could only ever backtest a signal from the
   last quarter, never the months candles currently reach. If the answer is
   yes, the remaining work is the bounded history endpoint and a tick-walking
   simulator (item 2 above) — a new build, not a small add given the existing
   simulators are bar-based throughout.

## What I would not do without asking again

Ship a template backtest that silently approximates the parts it cannot model.
A number you would not trust is better than one you would trust wrongly.
