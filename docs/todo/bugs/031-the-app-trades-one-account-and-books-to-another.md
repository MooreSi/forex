# 031 — The app trades account 26004592 and writes to account 25470480's database

**Status:** found 2026-09-09, live, **not fixed**. One definite defect
identified; whether it is what fired today is NOT proven.
**Money:** yes. Position sizing, the daily-loss halt and an ML feature are all
computed from the wrong account's balance, and that balance is corrupt.
**Found:** answering the owner's question about why the Reversal Engine seems
worse on this demo account than the previous one.

## The evidence

| | |
|---|---|
| account the bridge is connected to | **26004592**, balance **$970.57**, equity $960.97 |
| `mt5_credentials.login` | **26004592** — correct |
| database the running app has open (`lsof`) | **`forex_trader_demo.db`** |
| that file's registered account (`accounts.json`) | **25470480** — the OLD one |
| balance recorded in that file | **-$4,904.89** |
| trades written today | **6 in `forex_trader_demo.db`, 0 in `forex_trader_demo_26004592.db`** |

Both database files were migrated to schema 35 today, so **both were opened at
some point** — the app resolved to one and ended up on the other.

## What this costs

The Reversal Engine has NOT lost its training. `reversal_engine.db` is a single
shared file, not per-account, and it still holds 4,800+ signals. What it has
lost is coherence with the account it is trading:

- **Position sizing** is a percentage of balance (`suggest_lot_size(..., balance,
  risk_pct)`), and the balance it reads is -$4,904 instead of $970.57.
  Currently masked because the EA templates in use carry a fixed Anchor Lot,
  which bypasses the balance entirely — so this is live but not yet visible.
- **The daily-loss halt** is a percentage of that same number. A percentage of a
  negative balance is meaningless, which is why the recorded halt reasons read
  `40.0% of $135,081.16` and `20.0% of $882.95` on an account that has held
  neither.
- **`equity_drawdown_pct` is an ML feature** (added at v3). Every recent
  training row carries a value derived from the wrong account's corrupt ledger.
- **Channel scorecards and performance** are the old account's history with the
  new account's trades appended to them.

So the engine reasons about a $-4,904 account while trading a $970 one.

## The defect that can produce this

`frontend/app/__init__.py:438`, in the demo/live environment switch:

```python
settings_ctl.switch_environment_db(str(_DATA_DIR / f"forex_trader_{new_env}.db"))
```

**It rebuilds the path from the environment alone**, ignoring the per-account
registry. `run.py:399-401` resolves it correctly —

```python
_login   = _acct.login_for_env(get_mt5_credentials(), _env)
_db_path = str(_acct.resolve_db_path(cfg_module.DATA_DIR, _env, _login))
```

— and this line throws that away, pointing the app at `forex_trader_demo.db`
whatever account is logged in. Verified directly: `resolve_db_path(D, "demo",
"26004592")` returns `forex_trader_demo_26004592.db`, and with an empty login it
returns `forex_trader_demo.db`.

**What is NOT proven:** that this line is what fired today. It runs only when
the user toggles the live/demo switch, and there is no record of that happening
before the 09:20 startup. The mismatch is certain; this mechanism is a
candidate, not a conclusion. **Do not "fix" it and assume the problem is gone —
confirm the app opens the right file on a cold start first.**

`account_registry`'s own docstring anticipated the danger: *"if this resolver
ever hands back a new path for a login already using `forex_trader_demo.db`,
the app opens an empty file and 1,309 trades look like they vanished."* The
failure here is the mirror of that — the registry is right and something else
overrides it.

## Before fixing

**Decide what happens to the trades already in the wrong file.** Today's 6 (and
however many since the account changed) are recorded against 25470480's ledger.
Moving them is a data migration on live records; leaving them means the new
account's history starts incomplete. **That is the owner's call**, the same
class of decision as `reversal-engine/010`.

Also settle whether `forex_trader_demo.db`'s -$4,904.89 balance should be
carried across at all. It is roughly 30% fabricated (`reversal-engine/010`),
and the real account holds $970.57. Copying a corrupt balance to the correct
file fixes nothing.

## What to check first

1. Restart with no environment toggle and confirm via `lsof` which file the app
   opens. That separates "resolution is wrong" from "something overrides it".
2. If it opens the right file, the bug is only line 438 and it is narrow.
3. If it opens the wrong one, the resolution at `run.py:399` is failing
   silently — `login_for_env` returns `""` for unreadable credentials and
   `resolve_db_path` then returns the environment default **without raising**,
   so the error branch never logs.
