# 024 — a database per login would take your EA templates and settings with it

**Decision needed:** yes, before I build it.
**Money:** indirectly, and badly. A fresh database means no risk settings, no
EA templates and no credentials on the new account.
**Found:** 2026-09-02, investigating item 11 of your list.

## What you asked for

> "settings > MT5/Bridge - if i enter a new login on either the demo or live
> credentials this will create a new database for the specific account, any ML
> learning remains persistent across all accounts though so it doesn't lose
> this data."

The ML half is already safe. The rest is not, and the reason is that the
database holds much more than trades.

## Where things stand today

The database is split by **environment**, not by login:

```
forex_trader_demo.db   18.6 MB
forex_trader_live.db    0.3 MB
```

The ML models you were worried about are **not in there at all** — they are
separate files in the same directory (`bo_ml_*.joblib`, `re_ml_*.pkl`,
`gdc_ml_*.pkl`, `ml_signal_*.joblib`), as are the engine databases
(`breakout_signal.db`, `reversal_engine.db`, `test_signal.db`). Splitting the
trade database by login would not touch any of them, so ML learning survives
by construction. That part is fine.

## What a fresh database WOULD lose

Counted from your live demo database just now, read-only:

| Table | Rows | What it is |
|---|---|---|
| `ea_trade_templates` | **22** | your EA templates |
| `channel_performance` | 13 | per-channel history |
| `channel_strategy_rec` | 9 | the AI's template pick per channel |
| `channel_learned_rules` | 8 | learned parsing rules |
| `logic_keyword_lexicons` | 7 | learned keyword lexicons |
| `vantage_risk_settings` | 1 | risk per trade, harvest, lot sizing |
| `telegram_config` | 1 | your Telegram connection |
| `mt5_credentials` | 1 | the credentials themselves |
| `vantage_simulated_trades` | 1,309 | the trades |

So "new login, new database" as written means the new account starts with **no
EA templates, no risk settings, no Telegram, and no credentials** — and it
cannot read its own credentials to connect, because those live in the database
it just left behind. (`mt5_credentials` is already special-cased today: the
code keeps it in the demo database regardless of environment.)

Note also `dpm_calibration` and `dpm_trade_performance` are at 0 rows right
now, so DPM has no calibration to lose today — but it is learning, and it
accumulates into the per-account database, so the same question applies to it
the moment it has data.

## The decision I need

The work is not "split the file", it is "decide what is per-account". My
proposal, for you to correct:

**Per account** (it describes that account's trading):
`vantage_simulated_trades`, `vantage_signals`, `vantage_partial_closes`,
`vantage_pending_orders`, `vantage_simulation_account`, `consolidated_trades`,
`vantage_ladder_legs`, `vantage_closed_market_queue`, `trade_spread_cache`,
`mt5_connection_events`.

**Shared across accounts** (it is configuration or learning):
`ea_trade_templates`, `custom_strategies`, `strategy_param_templates`,
`vantage_risk_settings`, `telegram_config`, `email_config`,
`mt5_credentials`, `channel_learned_rules`, `logic_keyword_lexicons`,
`channel_parser_config`, `channel_strategy_rec`, `dpm_calibration`,
`app_config`.

**Genuinely arguable** — I would like your call:
`channel_performance` and `dpm_trade_performance`. Both are derived from
trades, so per-account is defensible; both are also what the recommendations
learn from, so shared is defensible. Mixing accounts' performance into one
channel history is the risk on one side; losing your channel judgement every
time you switch account is the risk on the other.

## Why I stopped

Doing this wrong is not a bug you notice — it is a new account that quietly
starts with default risk settings and none of your templates, on a live
platform. The migration also has to move 22 templates and 1,309 trades out of
a file the running app holds open.

I would rather show you the plan than reshape your database while you sleep.
