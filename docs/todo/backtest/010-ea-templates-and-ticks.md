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

All three phases shipped 2026-09-03. Phase 2 (option A) and phase 3
(templates listed automatically) landed first; phase 1 (ticks) landed after
the owner confirmed the measured cost was worth it.

Phase 1, what actually shipped:

* `mt5_bridge.py`: `/ticks`, backed by `copy_ticks_range`, bounded to one
  calendar day per request (the bridge itself refuses a wider range).
* `template_simulator.simulate_ticks()`: the same rules as the bar walk,
  resolved against real bid/ask instead of a bar's high/low — the same-bar
  "stop or target first" ambiguity does not exist here, because a real tick
  is only ever on one side of a level at a time. Refuses `trail_mode=candle`
  in addition to the bar walk's existing refusals: `CandleTrailLevel()`
  trails to the last 3 closed M15 candles, data this walk has no access to.
* `engine.run_backtest_ticks()` / `_simulate_ticks()`: template strategies
  only, same backstop as the bar dispatch (None rather than a guess).
* `TradingRuntime.get_ticks_range()`: the frontend's only path to the live
  bridge connection is through this facade, so this needed the owner's
  sign-off to raise `facade_baseline.json`'s method_count 88→89 — recorded
  there and in `structure_baseline.json`'s `_raised` (`runtime.py` 1507→1513,
  `mt5_bridge.py` 1344→1401).
* `frontend/pages/backtest.py`: "Ticks" as a fourth timeframe option, capped
  to 1 day per fetch and advising the ~90-day retention window.

Two real bugs were found and fixed while building this, both pre-existing in
the bar-based `simulate()` (shipped as part of phase 2, so live for less than
a day before the fix):

* **`trail_step` was never read.** `ApplyTemplateStepTrail` (mql5:2159-2171)
  only moves the stop once the improvement is >= `trail_step` pips — every
  template created by `ea_templates.py`'s `DEFAULTS` carries `trail_step:
  10.0`, so every step-trail simulation was trailing on any improvement at
  all, tighter and more often than the EA actually does.
* **A ladder whose levels sum to exactly 100% (the ordinary case) never
  recorded `close_price`.** That total is reached through the routine
  partial-close branch, not the dedicated "close everything" branch that is
  the only other place `close_price`/`close_bar` get set — so a fully-closed
  trade reported `outcome="tp"` with `close_price` stuck at 0.0.

One known gap, not fixed here — scope creep past what "build ticks" asked
for: the bar walk's own `trail_mode=candle` trails to the *previous bar*,
which only matches the EA's real 3-M15-candle lookback when the backtest
happens to run at M15 with a 1-candle lookback. Diverges from the EA at any
other timeframe. Tracked, not shipped as a silent approximation.

## What I would not do without asking again

Ship a template backtest that silently approximates the parts it cannot model.
A number you would not trust is better than one you would trust wrongly.
