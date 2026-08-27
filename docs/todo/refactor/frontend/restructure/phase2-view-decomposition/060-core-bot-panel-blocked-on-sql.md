# 060 — `core_bot_panel.py` cannot come under 800 without the SQL drain

**Status:** attempted 2026-08-27, reverted, blocked
**Blocks:** the `[loc]` drift item for `backend/src/services/positions/core_bot_panel.py` (1,712 lines)
**Depends on:** the SQL drain — money path, needs a demo session

## What was tried

A four-way split, following `/split-file`:

```
_panel_shared.py     the Screen type, button/callback helpers, channel lookups
_panel_schedule.py   the Trading Schedule editor
_panel_trade_ops.py  market orders, cancel pendings, risk-free, close, push SL
core_bot_panel.py    everything else
```

Pre-flight was clean — no module-level state, five test files, no undefined
names — and it worked: 1,712 → 1,138 with all 108 panel tests passing.

## Why it was reverted

**It does not reach 800, and it makes a different gate worse.**

`core_bot_panel.py` holds 6 SQL statements, baselined as one violation. All six
live in the trade-op functions and the channel-trade lookup they share. Splitting
those out moved the SQL from one non-repo file into two, so `[sql]` went 22 → 23:
one baselined violation became two new ones.

And the arithmetic does not work anyway. With everything SQL-bearing kept in
place, the module sits at roughly 1,524 lines. The remaining movable non-SQL
sections — registration (~91) and pause (~102) — leave it near 1,331. **There is
no arrangement that reaches 800 without relocating those six statements.**

## What it actually needs

The six statements belong in a repo module, which is what the `[sql]` gate has
been saying all along — SQL is allowed in `backend/src/db/`,
`backend/migrations/` and `*_repo.py`, and nowhere else. Four are reads
(open trades on a channel, working pending orders, a trade by id prefix); two are
`UPDATE vantage_simulated_trades SET stop_loss=?`.

Those last two are why this is not mine to finish unattended. They record a moved
stop on a live position. Relocating a query does not change what it does, but
`docs/system/rules/20-trading-safety.md` and CLAUDE.md's "stop and ask" list both
cover this, and the same demo session that covers the wider SQL drain covers it.

## Order of work

1. `_panel_repo.py` (the name matters — the gate identifies the data layer partly
   by filename) holding the six queries as named functions.
2. Re-run: `[sql]` should fall by one as a baselined violation is resolved, not
   spread.
3. Then the four-way split above, which is already known to work.

## One thing learned the hard way

The first attempt put `STRATEGY_NAMES` into `_panel_shared.py` via
`backend.src.controllers.trading_controller` — a **service importing a
controller**, which `services-never-import-controllers` enforces at zero. It came
straight back on the next contract check. Import it from
`backend.src.utils.models` in backend code; the controller re-export exists for
the frontend, which is the only layer that needs it.
