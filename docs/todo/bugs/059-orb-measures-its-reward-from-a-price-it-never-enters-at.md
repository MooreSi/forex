# 059 — ORB measures its reward from a price it never enters at

**Status: diagnosed, NOT fixed.** The fix changes stop distance, target
distance and therefore position size on a path that places real market
orders, so it needs owner sign-off and a demo session
(`docs/system/rules/20-trading-safety.md`, CLAUDE.md "stop and ask when").

Reported 2026-09-16 from two screenshots: the morning ORB email and the
in-app ORB/IVB tab disagreed, and "there was a definite breakout this
morning and it didn't properly capture it".

---

## 1. The reward is measured from the opening-range edge; the entry is not

[`orb_report.py`](../../../backend/src/services/analytics/orb_report.py), the
block beginning `breakout_edge = or_high if direction == "bullish" else or_low`:

```python
breakout_edge = or_high
stop   = breakout_edge - 0.50 * or_range
risk   = abs(breakout_edge - stop)
target = breakout_edge + 2.0 * risk
rr     = reward / risk                      # always exactly 2.0
```

Every number is anchored to `breakout_edge`. But `direction` only becomes
`bullish` at all when:

```python
broke_up = current_price > or_high
if broke_up and current_price > asia_high:
    direction = "bullish"
```

So the earliest price at which this is ever a tradeable signal is
`asia_high`, not `or_high`. With today's numbers:

| | value |
|---|---|
| London opening range | 4330.01 – 4336.21 (6.2 pts) |
| Asian range | 4275.46 – 4341.03 (65.6 pts) |
| `breakout_edge` (`or_high`) | 4336.21 |
| `stop` | 4333.11 |
| `target` | 4342.41 |
| reported `rr` | **2.00** |
| earliest possible entry (`asia_high`) | **4341.03** |
| distance to target from there | **1.38 pts** |
| distance to stop from there | **7.92 pts** |
| **realised R:R at the earliest possible fill** | **0.17 : 1** |

The 2.00:1 is computed against a price the system is structurally incapable
of entering at. It is not a rounding problem or a slippage problem: the two
prices are different by construction, and the gap is the distance between the
opening range and the Asian range.

**It scales with the range ratio.** Today the Asian range was 10.6x the
opening range. The wider the overnight range, the worse the realised R:R, and
the report's headline number never changes from 2.00.

## 2. That is why nothing was placed

[`orb_execute.py`](../../../backend/src/services/trading/orb_execute.py)
already refuses this case:

```python
target_already_passed = (
    (direction == "bullish" and current_price >= target)
    or (direction == "bearish" and current_price <= target))
if target_already_passed:
    ...  # skip, notify
```

The guard is correct and was added after a real incident the comment records
("a target of $4053.94, ~15pts on the wrong side of its own objective"). It
is firing because the setup is unreachable, not because the market did
anything unusual. By the time the in-app tab showed BREAKOUT — BULLISH at
4353.21, the target of 4342.41 was 10.8 pts *behind* price.

**So the engine correctly identifies breakouts and then declines to trade
them.** That is the reported symptom, and the guard is the messenger.

## 3. The opening range sits inside the confirmation range for half the year

This is the 07:00-vs-08:00 discrepancy between the two screenshots. Both
charts are right; the heading is wrong.

```python
london_open_local = london_now.replace(hour=8, ...)    # Europe/London
london_open_utc   = london_open_local.astimezone(utc)  # 07:00 UTC under BST
or_start, or_end  = london_open_utc, +15 min           # 07:00–07:15 UTC
asia_start = london_open_utc.replace(hour=0)           # 00:00 UTC
asia_end   = london_open_utc.replace(hour=8)           # 08:00 UTC
```

Two clocks in one calculation. Under BST the traded opening range
(07:00–07:15 UTC) is a **subset** of the confirmation range (00:00–08:00
UTC), so `asia_high` includes the hour *after* London opened — the breakout
move itself. The reference range absorbs the move it exists to confirm, which
inflates `asia_high` and pushes confirmation later, compounding §1.

Under GMT the two happen to line up, so this is a summer-only fault and
will disappear on its own in late October, which is exactly the kind of bug
that comes back next March.

The label `LONDON OPENING RANGE (08:00-08:15 UTC)` is wrong under BST. The
Asian label is genuinely UTC.

## What a fix has to decide (owner)

These are trading-policy questions, not implementation details:

1. **Anchor.** Should stop and target be measured from the confirmation
   price (`asia_high`/`asia_low`) rather than the opening-range edge? That
   keeps a true 2:1 but widens the stop, and with risk-based sizing a wider
   stop means a **smaller lot** for the same risk percentage.
2. **Or refuse the setup instead.** If the confirmation price is more than
   N x `or_range` beyond the edge, the opening range is not the structure
   being traded and the signal could be declined outright. That trades fewer
   days for honest geometry.
3. **Clock.** Anchor the Asian reference range to *London open* rather than
   08:00 UTC, so it always ends where the opening range begins.
4. **Neither of these is a stop-widening in disguise.** Whatever is chosen,
   `suggest_lot_size` must be re-checked: it is passed
   `_entry_approx = report["current_price"]` today, which is already a
   different price from `breakout_edge`, so the lot is being sized against a
   third price again.

## Tests that must exist before any of it

* A confirmed bullish breakout where `asia_high` is far above `or_high`
  asserts the realised R:R at the confirmation price, not at the edge.
* Today's exact numbers as a characterization case (4330.01/4336.21,
  4275.46/4341.03) — currently produces 0.17:1 and must produce whatever the
  chosen policy says.
* A BST date and a GMT date both assert that the Asian range ends where the
  opening range starts.
* The `target_already_passed` guard still fires for a genuinely stale report.

## Not to do

* Do not remove or loosen the `target_already_passed` guard to "let the
  trades through". It is the only thing standing between this geometry and a
  market order placed past its own take-profit.
* Do not change `_ORB_TARGET_R_MULT` to compensate. The multiplier is not
  wrong; the price it multiplies from is.
