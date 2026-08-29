# 017 — Backtests scored every timed-out trade as break-even

**Status:** found and **fixed** 2026-08-28, while writing the first tests this
file ever had.
**Touches money:** not directly — this is the Backtest page, which is offline
analysis. It touches money the slow way: it is where a strategy is judged
before it is trusted.
**Severity:** silent, systematic, and in the flattering direction.

## What was wrong

A backtested trade that is still open when it runs out of bars is a "timeout".
Seven of the eight simulators closed it like this:

```python
trade.close_price   = fill_price
trade.pnl_pts       = 0.0
trade.pnl_usd       = partial_pnl          # or 0.0
```

Closed **at the entry price**. So every trade that ran to max hold was scored
as break-even regardless of where the market had actually gone.

The eighth, `_run_ladder_strategy`, did it correctly and always had — it even
carries the comment *"Timed out — close remainder at last close"* and computes
the real move. That inconsistency is what makes this a bug rather than a
modelling choice: two strategies in the same report were being measured by
different rules.

## Why it matters

Max hold is 96 bars (~8h on M5) for most strategies and 288 (~24h) for the
GDVR family. A trade that drifts against you for a day and never hits its stop
or target is a real loss — and was reported as zero.

The bias only runs one way. A strategy that holds losers and drifts looks
break-even instead of losing; one that takes its stops cleanly is scored
honestly. That is exactly backwards from what a backtest is for, and it is
invisible unless you compare the points column against the P&L column — which
is how it was found.

## What changed

All seven now do what the ladder already did:

```python
last_close = candles[end_bar - 1]["close"]
move       = (last_close - fill_price) if is_buy else (fill_price - last_close)
trade.close_price = last_close
trade.pnl_pts     = move
trade.pnl_usd     = partial_pnl + move * remaining_lot * _USD_PER_PT_PER_LOT
```

Two of them (`be_runner`, `trail_stop`) never scale out, so they carry the full
`lot` to the end and have no `remaining_lot` — a first, mechanical pass got
that wrong and the tests caught it immediately.

Banked partials are unaffected: whatever was closed at TP1 stays banked, and
only the remainder is marked to market.

## What this changes in your numbers

**Backtest results will get worse, and they should.** Any strategy whose
trades often run the full hold will show lower win rates and lower totals than
it did yesterday. Nothing about live trading changed — the only consumer of
these simulators is the Backtest page (`frontend/pages/backtest.py` via
`backtest_controller`), which you drive by hand. It does not feed automatic
strategy selection; `strategy_ai`'s "backtested" references are to a static
template map, not a live call.

If a strategy was picked partly on backtested numbers, it is worth re-running
now that the timeout arithmetic is honest.

## Tests

`tests/core/test_backtest_simulators.py` — the file had **0% coverage** before
this. 44 tests, parametrized across all ten simulators, covering the timeout
pricing in both directions, that a flat market still books break-even (the case
the old code got right by accident), that the points and P&L columns agree,
that stops fire on the correct side for the direction, and that a banked
partial survives a later stop-out.

Seven mutants, all killed — including reverting the fix, zeroing the points
again, flipping the move's sign, reading the wrong bar, and regressing the
ladder to the broken shape.
