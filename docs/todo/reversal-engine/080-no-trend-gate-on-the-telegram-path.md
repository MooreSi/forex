# 080 — The Telegram execution path has no trend filter

**Status:** **BUILT 2026-09-09, off by default, NOT DEMOED.** Turn it on at
Trading > Strategy > Risk Settings, "Only trade with the trend".
**The single largest loss of 2026-09-08: -$718.95.**
**Money:** yes — it decides whether an order is placed.
**Found:** 2026-09-08, [data-inspect/004](../data-inspect/004-why-2026-09-08-lost-1270.md).

## What is missing

`governor.check_pre_trade_filters` applies exactly two gates:

1. minimum TP1 R:R
2. a directional cap on *concurrent unprotected* same-direction trades

Neither asks whether the higher timeframe is going the other way. So a channel
posting BUY signals into a sustained downtrend has every one executed.

On 2026-09-08, gold fell from 4438 to 4391 and `GOLD DIGGERS INSTITUTIONAL`
lost **-$718.95 over 20 trades, 5 wins to 15 losses**, almost all BUYs. The
directional cap limits how many run at once, not how many are taken in a day.

## The engine already computes what is needed

The Reversal Engine reads `htf_bias` per signal and uses it (imperfectly — see
[090](090-level-score-bypasses-the-bias-filter.md)). The Telegram path does not
consult it at all. **This is one signal, computed already, applied on one route
and not the other** — the same shape as the three independent copies of the IME
gate that bugs/024 was about, in reverse.

## What to build

A bias gate on the shared pre-trade path, so it applies to every source rather
than to whichever route remembers to ask. Decide with the owner whether it
blocks outright or only downsizes, because a channel he trusts may be
deliberately counter-trend.

**Measure before choosing the rule.** Today is one day. Before making this a
hard block, check across the full history whether counter-bias Telegram trades
lose in general or only lost today — `re_signals` carries `htf_bias`, and the
trade rows carry the source.

## Test first, then demo

It stops orders being placed. Tests before code, and it does not go live
without the owner watching.


---

## Built 2026-09-09 — and the diagnosis above was incomplete

**This file said the Telegram path had no TREND filter. It has no pre-trade
filter at all.** `resolution.py` guards the whole block:

```python
if strategy not in _self_level_strategies and not _is_template:
    filter_err = check_pre_trade_filters(...)
```

**Every trade that lost money on 2026-09-08 was a template strategy**
(`template:GD Instituational - single`, `template:30 TP1 SL50 and Trail`), so
the R:R minimum and the directional cap did not run on them either. A bias gate
added inside `check_pre_trade_filters` — the obvious place, and where this file
originally pointed — **would not have stopped a single one of them.**

The gate is therefore its own check, deliberately outside that condition, and a
test asserts its position relative to `and not _is_template` so it cannot be
quietly moved back inside.

### The measurement this file asked for, done first

Across every executed Reversal Engine signal on record, not just 2026-09-08:

| | n | win % | net |
|---|---|---|---|
| with the bias | 369 | 61.8 | **+$101.41** |
| against it | 201 | 56.2 | -$1,210.98 |
| neutral | 184 | 57.1 | -$1,234.06 |

**Trading with the bias is the only profitable group in the entire history.**
So the rule generalises; it was not a one-day artefact.

### What shipped

`governor.htf_bias_blocks(direction, htf_bias, rs)` — one function, called from
the shared open path AND the Reversal Engine, with a test asserting both use it
rather than growing a second copy.

`governor.current_htf_bias(bridge, rs)` supplies it, cached 60s, and **makes no
bridge call at all while the toggle is off**. It delegates to
`level_detector.get_htf_bias`, the implementation whose recorded output is the
evidence above. (There is a second implementation in
`test_signal/signal_generator.compute_htf_bias`; they must not both become
"the" bias.)

**Off by default** (migration 35, `htf_bias_gate_enabled`), so nothing changes
until the owner turns it on. **Not demoed** — it refuses orders that would
otherwise be placed.

**Neutral does not block**, though it loses as much as counter-bias does. "No
clear trend" is a different claim from "the trend is against you", and blocking
184 trades' worth is a bigger change than was asked for. See
[090](090-level-score-bypasses-the-bias-filter.md).


---

## Two routes were still uncovered — closed 2026-09-09

The gate as first shipped covered the shared open path
(`resolution.resolve_open_trade_params`) and the Reversal Engine. **Two routes
that place real orders bypassed it**, found by checking rather than assuming
after it had been switched on live:

| route | how it reaches the broker |
|---|---|
| `instant_entry.py` (Immediate Market Entry) | never calls `resolve_open_trade_params` |
| `limit_order_signal.py` (pending / limit) | `place_pending_order()` and `open_trade()` directly |

Both say so in their own comments. IME already carried its own copies of the
**session**, **Trading Schedule** and **news-blackout** gates for exactly this
reason — the bias gate was the fourth one it needed and did not have.

The limit path needed the check placed before **both** of its exits: the
pending order and the `lk_entry_realignment` branch that turns a breached limit
into a market order. Gating only the first would have left the second open, and
a mutation moving the gate below the realignment branch is one of the four the
tests kill.

Ten tests in `tests/trading/test_bias_gate_covers_every_order_path.py`, red
first. They are **structural and say so**: the gate's logic is unit-tested in
`tests/risk/test_htf_bias_gate.py`, and what these pin is that each route calls
it, before it places anything, through the shared `governor.htf_bias_blocks`
rather than a hand-rolled comparison.

**Those tests fell into the comment-matching trap twice while being written** —
first matching `place_pending_order()` in a module docstring, then in the
gate's own explanatory comment — and now strip comments and docstrings before
asserting on order. Recorded because a source check that reads its own
explanation and passes is precisely the failure
`structural-tests-match-comments` warns about.

Still off by default and still not demoed.


---

## A THIRD route was uncovered — the main one — closed 2026-09-09 (night)

The audit above listed IME and limit orders. It missed
**`scan_auto_execute`: a fresh Telegram signal whose price is already inside
its entry zone, opened at market on arrival.** That is the ordinary case, and
it is the 2026-09-08 case.

**Found by writing the end-to-end test, not by reading.**
`tests/e2e/test_trend_gate_end_to_end.py` drives a real signal through the real
pipeline against `FakeMT5Bridge`. On its first run the two refusal tests failed
and all three controls passed: a BUY opened at market against a bearish bias
with the gate **on**. A probe confirmed `htf_bias_blocks` was never called —
zero invocations, one position.

**The module says it about itself**, of the *schedule* gate:

> This path opens via core_open_trade.open_trade directly and never calls
> resolve_open_trade_params, which is where the schedule gate lives for every
> other route -- so a fresh Telegram signal executed regardless of the
> schedule, while queued zone-fills, pending-order fills, IME trades and the
> internal engines were all correctly blocked.

That gap was patched there for the schedule on 2026-08-06, and for IME on
2026-07-23. The bias gate arrived on 2026-09-09 and repeated it a third time.

**So between the gate being switched on and this fix, it did not cover the
route the file was written about.** GOLD DIGGERS INSTITUTIONAL posting BUYs
into a falling market is exactly a signal arriving with price in its zone.

### Fixed

`htf_bias_blocks` now runs alongside the schedule and news gates in
`execute_auto_signal`, in the same position and below the IME follow-up block
for the same stated reason. It makes no bridge call while the toggle is off.

Four mutants: the branch deleted, the branch made unreachable, and the bias
hardcoded were killed at once. **Hardcoding the direction to "BUY" survived**,
because every test in the file used a BUY signal — a gate that ignores
direction entirely was invisible. Two SELL cases were added and it dies.

One more thing the controls earned: the first version of the fix referenced a
local `direction` that does not exist in that function, and crashed inside the
scan's per-message try/except. The refusal tests went green — because nothing
opened — while all three controls went red. Without them it would have looked
like a working gate.


---

## A question for the owner, and the guard that stops a fourth miss

### Three manual routes are exempt, and that has NOT been confirmed

`manual_market_order.py` (the Market Order button), `manual_limit_order.py`
(Create Limit Order) and `bot_trading.py` (Telegram bot commands) all reach the
broker and none consults the bias gate.

**The reading applied is that a manual order is the operator overriding the
system on purpose**, and that a button refusing because the H1 trend disagrees
would be surprising. `tests/core/test_manual_order_exemptions.py` already draws
this line for the other gates: manual orders are exempt from the **scheduling**
gates (trading schedule, news blackout) and NOT from the **protective** ones
(the risk halt, `max_open_trades`).

The bias gate is arguably protective, which would put it on the enforced side.
**That is the owner's call and it has not been made.** Nothing was changed;
the exemption is written down so the question is visible instead of being
implied by absence — which is exactly how the three misses survived.

### The guard

`tests/trading/test_every_order_route_declares_its_bias_gate.py` enumerates
every module that reaches the broker and requires each to be listed as either
GATED (and to actually consult the gate) or EXEMPT (with a written reason). A
new order route fails the suite until someone decides which it is.

Two mutants confirm it bites: a new module that calls `open_trade` and is in
neither list fails, and stripping the gate out of `scan_auto_execute` fails.

**This, not another gate, is the thing that would have caught all three
misses.** The gate was believed complete twice, and both times the audit was a
person reading code and listing what they remembered.


---

## First live measurement, 2026-09-10

The gate was switched on 2026-09-09. Measured over every Reversal Engine signal
raised since, using the engine's own tracked outcomes (it follows a signal to a
result whether or not it was executed, which is how it learns):

| | n | win rate | P&L |
|---|---|---|---|
| **blocked by the gate** | 43 | **74%** | **-$453.88** |
| executed | 12 | 67% | +$99.37 |

And the blocked set split by outcome:

| | n | total | average |
|---|---|---|---|
| winners | 32 | +$516.52 | **+$16.14** |
| losers | 11 | -$970.40 | **-$88.22** |

**A 74% win rate that loses money.** The losers are 5.5x the size of the
winners, which is the payoff problem this whole directory exists about — the
engine's history is 59.4% wins at +0.642R against -1.161R. The gate is
refusing exactly that shape: trades that usually win a little and occasionally
lose a lot.

**This is the first evidence the gate earns its place on this account**, rather
than on the historical measurement it was designed from.

### What this does NOT establish

* **n is small.** 43 blocked and 12 executed, over roughly one day.
* **The blocked P&L is paper.** It assumes a blocked signal would have been
  managed identically — same template, same TP ladder, same partial closes. A
  real fill can differ, and the biggest blocked loser (-$88) is larger than any
  real loss on the account that day (~-$50), which is itself a hint that the
  virtual path and the EA do not manage the same way.
* **One day, one regime.** The bias was bullish most of the session and flipped
  bearish overnight, so nearly all of these were SELLs refused into a rise.

Worth re-running after a week. The query is the `live_exec_status` /
`outcome` join above.

### Two observations from the same data

`live_exec_status` also shows **17 signals lost to
`error:EA rejected template order: not enough money`**, all between 05:15 and
11:47 on 2026-09-09, none since. That is a margin failure during the account's
low point, not an ongoing fault — but it is 17 signals that never reached the
broker, and nothing surfaces it outside this column.

And one row reads `error:EA Template refused: the chart is running EA v1.05...`
— [bugs/033](../bugs/033-a-stale-ea-build-was-invisible.md) refusing a template
on the stale build, in production, exactly as intended.
