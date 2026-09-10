# 042 — Turning the Risk Governor on would halt trading on the first close

**Status:** **FIXED 2026-09-10, test-first, four mutants killed** — option 1,
on the owner's instruction ("fix the peak_balance watermark so the governor can
go on, but don't turn it on"). **The governor is still OFF; nothing turned it
on.** Applies to the running install **at the next restart**, not now — no
database was hand-edited. Found 2026-09-09 (night) reading the live halt state
on the demo account.
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


---

## What was done, 2026-09-10

**Option 1, as code rather than as a hand-edit.** The watermark was not reset by
typing a number into the live database. `db/account_registry.resolve_db_path`
now stamps `peak_balance_account` on every resolve that names an account, and
clears `peak_balance` when the stamp is absent or names a different account.
`close_trade._update_peak_balance` then sets it again from the **live** balance
on that account's next close. Nothing in the frozen close path was touched.

Why that shape rather than a number:

- The reset value should be the live MT5 balance, and that is only knowable
  from inside the running app. Any figure written from outside would be a
  guess — the internal sim ledger read $834.49 tonight, which is exactly the
  number `rg_check_halt` is documented never to use.
- It heals the **cause**. `app_config` is copied by `_seed_shared_tables` as an
  install-wide table, so the next account added would have inherited the
  watermark again.
- It needs no write to a database the app currently has open.

**State on the install, read read-only 2026-09-10 21:00:**

```
forex_trader_demo_26004592.db   peak_balance = 2403.25   (the active file)
forex_trader_demo.db            peak_balance = 2403.25
forex_trader_live.db            peak_balance absent
```

At the next restart the active file's watermark is cleared and stamped
`26004592`. Until that account's next close there is no watermark, so the
total-drawdown halt cannot fire — the same state a fresh install is in.

**Not done, deliberately:** `risk_governor_enabled` is untouched (still 0), and
the stale `risk_halt_reason` / `trade_pause_until` pair in the active file was
left alone. That pause expired on 2026-08-30, so it holds nothing back, and
clearing an inherited *pause* is a change in the permissive direction — a
separate decision from the watermark.

**Still yours:** the three items in
[handover/011](../../simon-handover/011-your-halt-settings-do-not-match-what-you-confirmed.md)
— governor on, daily loss 3%, drawdown 10%. Turning the governor on is now safe
from the watermark's side, but **it has never been demoed on this account**: the
first close after switching it on is the first time the total-drawdown branch of
`rg_check_halt` will have run here at all.

Tests: `tests/db/test_account_db_registry.py::TestThePeakBalanceWatermarkIsAccountScoped`
(6 tests, written and watched fail first; mutants killed — owner check inverted,
delete loop removed, stamp not written, re-anchor not called).
