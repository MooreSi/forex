# 064 — The daily profit target un-reaches itself, and the limit path never asks it

**Status: NOT FIXED. Both halves need the owner** — one is a money-policy
decision (`docs/simon-handover/038`), the other is a gate on the order
placement path. Nothing has been changed.

Found 2026-09-16, from the owner asking why ticket **2031441425** was placed
and filled after the day's $200 target had been reached.

## The short answer

It had been reached, at 07:10. By 20:12 it had **un**-reached itself, because
the gate compares a live running sum against the target and nothing remembers
that the sum was ever over it. A losing trade closing at 19:32 pulled the day
back under $200 and automated entry resumed.

The loss that did it was booked by the schedule guard itself.

## Defect 1 — the target is a running sum, not a latch

`schedule.py:497 check_trading_schedule`:

```python
daily_target = get_daily_profit_target()
if daily_target > 0 and not is_daily_profit_target_resumed(now):
    day_pnl = _day_realized_pnl(now)
    if day_pnl >= daily_target:
        return False, "daily profit target reached (...)"
```

`_day_realized_pnl` re-runs `SUM(net_pnl) WHERE status='closed' AND open_time
>= midnight` on every call. There is no persisted "reached today" flag. So the
gate holds only while the *current* total is above the target, and releases
the moment it drops back under.

The design note at `schedule.py:262` says the resume override is stored as a
date "Same reasoning as computing profit on demand instead of keeping a
running counter." Computing on demand is right for the numerator. It is wrong
for the *decision*, because the decision is meant to be one-way for the day —
the reason text says so: "resumes tomorrow".

### The live sequence, 2026-09-16

Target $200, schedule enabled, active Wednesday window 00:00–23:59 (its own
per-window target is also $200, so both gates move together). The operator did
**not** use the resume override — `trading_schedule_daily_target_resumed_day`
is unset.

Cumulative closed P&L for trades opened today, ordered by close time:

| close | trade | cum | gate |
|---|---|---|---|
| 07:00:07 | +32.14 | 162.64 | open |
| **07:10:21** | +48.04 | **210.68** | **HELD** |
| 11:08:59 | +2.12 | 212.80 | HELD |
| **19:32:30** | **-27.00** | **185.80** | **RELEASED** |
| 20:14:09 | +56.56 | 242.36 | — |

The gate held for 12h22m, then let go, and ticket 2031441425 was placed at
20:12:46 and filled at 20:12:48.

### The part that makes it a loop

The -$27.00 at 19:32:30 is ticket **2030749724**, and its `exit_reason` is
`trading_schedule_blocked`. It is the schedule guard's own work: the order was
placed at 19:31:51, `resting_revalidation` tried to withdraw it at 19:32:19
and lost the race, it filled at 19:32:21, and `_events.py:419` force-closed it
at 19:32:30 because the schedule said no.

**The enforcement action booked a loss, and that loss is what re-opened
trading.** A gate that pays to shut itself and re-opens because it paid is
worse than no gate: the harder it works, the sooner it quits.

## Defect 2 — the limit-order placement path has no schedule gate at all

`handle_limit_order_signal` (`limit_order_signal.py:215`) never calls
`check_trading_schedule`. In `scan_messages.py:411`, a `[LIMITS]`-shaped
signal on a non-grid channel branches away from `_execute_auto_signal_impl`
— which **does** gate, at `scan_auto_execute.py:212` — and goes straight to EA
pending-order placement. The `sess_ok` / `skip_reason` values passed in from
`resolve_strategy_and_skip_reason` cover the Trading Markets session gate and
auto-eval, not the schedule. `resolve_open_trade_params` (`resolution.py:222`)
holds the gate for the *fill* path and is never reached at placement.

This is the **fifth** route to miss this gate. `scan_auto_execute.py:195`
documents the same class of defect found 2026-08-06 (ticket 1720148940, opened
12:25 against a window that ended at 12:00), and `core_instant_entry.py` had
it patched 2026-07-23.

### What it cost today

13 pending orders were placed while the day was over target. Eleven were
cleaned up afterwards by `resting_revalidation`'s withdrawal sweep, two were
not:

| ticket | placed | outcome |
|---|---|---|
| 2025024913 | 07:13:11 | withdrawn 07:13:37 (26s later) |
| 2025037516 | 07:15:21 | withdrawn 07:15:38 |
| 2025257289, 2025680509, 2025793919, 2026390502, 2027850602 | 07:53–14:08 | withdrawn, 12–49s later |
| 2026665024, 2028928347, 2028935207, 2028978350 | 11:13–15:52 | never filled, no trade row |
| **2030749724** | 19:31:51 | **filled 19:32:21, force-closed 19:32:30, -$27.00** |
| **2031441425** | 20:12:46 | **filled — gate had already released (defect 1)** |

So the existing containment mostly works, and the cost of defect 2 in
isolation today is the one -$27.00 fill that beat the sweep by two seconds.
That is not a small cost, because it is also the input to defect 1.

The two defects are independent and both need fixing. Fixing only defect 2
still leaves the target un-latching on any ordinary losing trade. Fixing only
defect 1 still lets the app send orders to the broker it has already decided
it does not want, and rely on a race to take them back.

## The fix, not applied

**Defect 1 — latch the target.** On the first `check_trading_schedule` call
where `day_pnl >= daily_target`, persist a reached-day key in the same shape
as `DAILY_TARGET_RESUMED_KEY` (`"%Y-%m-%d"`, expires at midnight by
construction, nothing to clean up). Gate on `reached_day == today OR day_pnl
>= target`, not on the sum alone. `resume_past_daily_profit_target` stays the
only way back in, unchanged. `daily_profit_target_state`'s badge reads the
same latch so the header stops disagreeing with the gate.

The per-window target at `schedule.py:542` has the identical shape and the
identical flaw. Same treatment, keyed per window per day.

**This needs the owner's answer first**: should a later loss ever be able to
un-reach the day's target? See `docs/simon-handover/038`. I would say no, but
it is a money rule, not a code opinion, and the latch is the wrong thing to
build if the answer is "yes, it should track the live total".

**Defect 2 — gate the placement.** `check_trading_schedule(source=channel_name)`
at the top of `handle_limit_order_signal`, after the `sess_ok` and
`per_signal_skip` checks and before the EA-health check, returning a
`skip_reason` in the same form as its siblings. Same call, same argument, same
position in the flow as the other four sites. That turns `_events.py:419`'s
force-close back into a backstop for the genuine race (an order resting from
before the target was hit) instead of the primary control.

Also worth the owner's eye: `check_news_blackout` and the HTF bias gate are
missing from this path for exactly the same reason. Not in scope here, but
they are the same three gates `scan_auto_execute.py` carries together, and
this path carries none of them.

## Why no test yet

Both changes sit on the path to `open_trade` / EA order placement. Per
`CLAUDE.md` they need the owner and a demo session. The tests are written
first when the decision lands — the red ones being:

* a day that crosses the target and then falls back under it still blocks
  (defect 1, currently green-when-it-should-be-red);
* `handle_limit_order_signal` returns a skip and places nothing when
  `check_trading_schedule` says no (defect 2);
* the force-close at `_events.py:419` still fires for an order that was
  resting before the target was reached — the case that is not a bug.

## Evidence

Live demo DB `forex_trader_demo.db` (`vantage_simulated_trades`) and
`forex_trader.log`, both 2026-09-16, read from a scratchpad copy. The gate's
own log lines name the number it was holding on:

```
07:13:06 [RE-Engine] schedule blocked live exec RE-C8B3F9 --
    daily profit target reached ($210.68 of $200.00) -- resumes tomorrow
```

Nothing after 19:32:30 says that, because by then it was $185.80.
