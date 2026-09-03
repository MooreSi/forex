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

What is missing:

1. **A history endpoint.** The bridge serves `/candles`, `/candles_range` and
   `/candles_symbol`. Tick history needs its own, backed by
   `copy_ticks_range`.
2. **Volume, which must be measured before anything is built.** M1 is ~985
   bars/day. XAUUSD ticks are orders of magnitude more, over an HTTP bridge
   running under Wine. **I have not measured it and will not guess.** The first
   task is a one-off probe: fetch one hour of ticks, report count and bytes,
   and decide from that whether a day is workable and how far back Vantage
   actually keeps them.
3. **Simulators that walk ticks.** Each currently iterates bars. Either they
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

## What I need from you

1. **Option A, B or C for phase 2.**
2. **Whether ticks alone would be useful.** If the honest answer is that you
   want templates and ticks together, phase 1 still goes first — it is
   independent and it de-risks phase 2's data path.
3. **Which templates matter.** If the five or six actually in use avoid grid
   mode, option A covers everything real and the exclusion list is empty in
   practice.

## What I would not do without asking again

Ship a template backtest that silently approximates the parts it cannot model.
A number you would not trust is better than one you would trust wrongly.
