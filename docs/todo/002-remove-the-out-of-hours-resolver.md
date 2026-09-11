# 002 — Remove the Out of Hours resolver and its columns

**Status:** Draft — needs owner approval of §3 before any code.
**Raised:** 2026-09-11, owner: *"yes spec the removal of the resolver and
columns"*, following the removal of the Out of Hours card
([handover/020](../simon-handover/020-out-of-hours-still-runs-on-utc.md)).
**Touches money:** yes — `get_effective_strategy` chooses which strategy
manages an open trade. Owner sign-off + a demo session, per golden rule 4's
neighbourhood, even though the close path itself is untouched.
**Domain:** [risk](../system/domains/risk/README.md) (read: the Out of Hours
entry and the two-clocks note).

---

## 1. What is wrong today

The card is gone (2026-09-11, `e0f03c9`) but the machine behind it is not.
`get_effective_strategy` still reads eight `ooh_*` columns on every monitor
cycle and can still override the strategy managing an open trade. There is now
**no screen anywhere that shows or sets any of it.**

That is the worst of the three possible states:

| | visible | live |
|---|---|---|
| before 2026-09-07 | no | yes ← the state handover/020 was raised to complain about |
| 2026-09-07 → 2026-09-11 | yes | yes |
| **today** | **no** | **yes** ← same as the first row, now with the control deliberately deleted |

`ooh_enabled` is **0** on the live install (read 2026-09-11), so nothing is
being overridden. Nothing prevents it being 1: the sync channel mirrors risk
settings between the Mac and the VPS, the per-account seed copies
`vantage_risk_settings` wholesale into a new account's database, and a restored
backup carries whatever it carried. Each is a route to a strategy no screen can
show.

## 2. What changes

Delete the feature, not just its interface.

**Code**
- `risk_settings_repo.get_effective_strategy` and `_ooh_now` — deleted.
- `monitor_cycle.py:254` — the `_eff_strategy`/`_ooh_active` pair goes; each
  trade uses `trade.get("strategy", STRATEGY_SCALE_OUT)`, which is what it
  already does whenever `_ooh_active` is false, i.e. always, today.
- `telegram/alerts.py:_strategy_label` — the `OOH:` branch goes. DPM keeps
  precedence; the template and per-trade branches are unchanged.
- `frontend/pages/trading/_active_trades.py:176` — the `OOH:` badge goes.
- Re-exports: `db/database.py:292`, `services/risk/settings.py:41`,
  `controllers/trading_controller.py:44`.

**Schema** — a new numbered migration (39) dropping the eight columns from
`vantage_risk_settings`:
`ooh_enabled`, `ooh_start_time`, `ooh_end_time`, `ooh_strategy`,
`ooh_date_from`, `ooh_date_to`, `ooh_date_active`, `ooh_timezone`.

This is the **first destructive migration in the registry** — every one of the
38 before it adds. Three things follow from that and they are the reason this
is a spec and not a commit:

1. `ALTER TABLE … DROP COLUMN` needs SQLite ≥ 3.35 (3.51 here, fine) and fails
   if a column is used by an index or view. Checked: none of the eight is.
2. It is **forward-only and irreversible.** A database migrated to 39 cannot be
   opened by an older build that expects the columns. The daily backup is the
   only way back.
3. The registry's own test asserts `"ooh_strategy" in cols(...)` at head
   (`tests/migrations/test_migration_registry.py:61`). That assertion becomes
   the opposite one — a legitimate update, since the schema it characterises
   deliberately changed, and it must be made deliberately rather than deleted.

**Tests deleted with the feature:** `tests/risk/test_effective_strategy.py`
(17) and `tests/core/test_ooh_timezone.py` (10). Deleting tests for deleted
behaviour is not "editing a test to make a change pass" — but it is 27 tests,
and the coverage ratchet must be re-read afterwards rather than assumed.

## 3. The decision this needs before it starts

**Drop the columns, or keep them and delete only the code?**

- **A. Drop them (this spec as written).** The setting cannot be turned on by
  any route, because it no longer exists. Costs the first destructive migration
  and a one-way door.
- **B. Delete the resolver, leave the columns.** No migration, no risk to
  anyone's database, fully reversible. The columns sit there inert, read by
  nothing. The next person to find them wonders what they were.

A is what "remove the resolver and columns" asks for and is the cleaner end
state. B is what this would do if the change had to ship unattended.

**ANSWER:**

## 4. What must NOT change

- **Which strategy manages a trade, for every trade, on this install.** With
  `ooh_enabled = 0` the resolver returns `(base, False)` and the caller uses
  the per-trade strategy. After the change the caller uses the per-trade
  strategy directly. The observable behaviour must be **byte-identical**, and
  that equivalence is the whole safety argument for this change.
- **DPM precedence in `_strategy_label`.** DPM is checked before OOH today and
  must still win afterwards.
- **The Trading Schedule**, its tab, its card, its per-source windows and its
  tests. It is a different feature that gates entry; it is not touched.
- **`trade_strategy`**, the base strategy column, stays. Only the `ooh_*` eight
  go.
- **Every other migration step and the schema version stamp.** The new step is
  additive to the registry even though its SQL is destructive.
- **These pass unmodified:** `tests/core/test_monitor_cycle*`,
  `tests/frontend/test_risk_card_has_no_out_of_hours.py`,
  the Trading Schedule tests, and `tests/refactor/*` (structure, orphans,
  undefined names).

## 5. Non-goals

- Does **not** change the Trading Schedule in any way — not its windows, its
  timezone, its per-source toggles or its profit targets.
- Does **not** change how any strategy manages a trade. It removes a switch
  that chooses between strategies; it does not touch the strategies.
- Does **not** revisit the UTC-versus-local-clock question. That question dies
  with the feature.
- Does **not** touch the close path, order placement or sizing.
- Does **not** remove `display_strategy_id`, `dpm_*`, `immediate_market_entry`
  or `exclude_high_risk`, which were added by the same migration step 4.

## 6. Test plan — written before the code

| # | Assertion | Negative control (how do I know it can fail?) |
|---|---|---|
| 1 | With a risk-settings row carrying `ooh_enabled=1`, a window covering now, and `ooh_strategy='trail_stop'`, `monitor_cycle` manages an open trade with **the trade's own strategy** | Run it against today's code first: it must report `trail_stop`. If it does not, the test is not reaching the override and proves nothing |
| 2 | `_strategy_label` never returns a string starting `OOH:`, with the same row as #1 | Same row against today's code returns `OOH: Trail Stop` |
| 3 | `get_effective_strategy` is gone from `db.database`, `services.risk.settings` and `trading_controller` | Assert the attribute is absent — re-add one re-export and the test must fail |
| 4 | After migration 39, `PRAGMA table_info(vantage_risk_settings)` contains none of the eight | Run against a pre-39 fixture database: all eight present |
| 5 | Migration 39 on a **legacy** database that never had the columns (pre-step-4 fixture) does not raise | Drop a column that is not there without the guard and the step raises `no such column` |
| 6 | `verify_critical_schema` still passes and the version stamp reads 39 | Stamp 38 and assert it is read as 38 first |
| 7 | The Trading Schedule still gates entry exactly as before | The existing schedule tests, unmodified |

Tests 1 and 2 are the ones that matter: they are the equivalence argument in
§4, and both must be written and **watched fail on today's code** before
anything is deleted.

## 7. How we will know it worked

- `python -m tools.checks all` green, including the coverage ratchet after 27
  tests are deleted.
- A demo session on the demo account: open a trade, let the monitor cycle
  manage it, confirm the managing strategy in the log and the Telegram label
  are the trade's own — before and after.
- The live database opens, `PRAGMA table_info` shows the eight gone, and the
  app boots without `verify_critical_schema` complaining.

## 8. Verification checklist — fill in when it ships

- [ ] Tests 1 and 2 written first and seen to fail on the old code
- [ ] `python -m tools.checks all` green, output pasted
- [ ] Migration 39 replayed against a copy of the live database, not a fixture
- [ ] A backup of the live database taken **before** the first run at 39
- [ ] Owner sign-off recorded, with the §3 answer
- [ ] Demo session held; managing strategy unchanged before and after
- [ ] **No real or demo order was placed, closed or modified to verify this**
- [ ] `docs/system/domains/risk/README.md` Out of Hours entry deleted, and
      handover/020 closed with a pointer here
