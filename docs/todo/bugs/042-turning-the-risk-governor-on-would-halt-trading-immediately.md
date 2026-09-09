# 042 — Turning the Risk Governor on would halt trading on the first close

**Status:** OPEN, **nothing changed.** Found 2026-09-09 (night) reading the
live halt state on the demo account.
**Money:** yes — it decides whether the app trades at all.

## The state, read live

```
peak_balance            = 2403.25          (app_config watermark)
broker balance          =  888.21
max_total_drawdown_pct  = 40.0
risk_governor_enabled   = 0
```

`governor.rg_check_halt(rs, 888.21)` returns, right now:

```
Total drawdown 63.0% from peak $2,403.25 (limit 40%)
```

**That condition is true and has been for some time.** It does not halt
anything today, because the drawdown check lives in `rg_apply_halts_on_close`,
and `close_trade` only calls that when the Risk Governor is on:

```python
if bool(_rg_rs.get("risk_governor_enabled", 0)):
    await ... rg_apply_halts_on_close(...)
```

The **daily-loss halt** and the **give-back guard** are called separately and
unconditionally, which is why those still work with the governor off. The
**total-drawdown halt does not.**

## The two consequences

### 1. The 40% drawdown limit is currently doing nothing

Worth knowing on its own. Settings shows a Max Total Drawdown of 40%, and with
the governor off it is not enforced on any close.

### 2. Turning the governor on would halt trading immediately

[handover/011](../../simon-handover/011-your-halt-settings-do-not-match-what-you-confirmed.md)
records the plan: *"Before this app runs on a live account, the cap goes back
to 3% and the risk governor goes back on."* On the first close after that
switch, `rg_check_halt` returns the line above and trading pauses.

It would look like the governor is broken. It is not — it is doing exactly what
it says, against a watermark from a different era.

## Where the watermark came from

`peak_balance` is monotonic. `close_trade._update_peak_balance` raises it
whenever the live balance exceeds it and **nothing ever lowers it** — not the
per-account database split, not a deposit change, not the
[031](031-the-app-trades-one-account-and-books-to-another.md) repair that moved
182 trades to the correct account, and not the
[reversal-engine/010](../reversal-engine/010-repair-the-fabricated-losses.md)
repair of ten fabricated P&L rows.

$2,403.25 predates all of that. Whether this account (26004592) ever really
held it has not been established.

## The decision

1. **Reset `peak_balance` to the current balance** before enabling the
   governor, so the drawdown measures from now.
2. **Reset it to a figure you choose** — the real high-water mark for this
   account, if you know it.
3. **Leave it**, and accept that enabling the governor halts trading until the
   account climbs back above 60% of $2,403.25.

**Not chosen here.** It is a protective watermark; moving it makes the
drawdown halt more permissive, which is a money decision even when the current
value is probably wrong.
