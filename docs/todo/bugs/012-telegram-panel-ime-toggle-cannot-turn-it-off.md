# 012 — The Telegram panel's IME button can turn it on but never off

**Status:** FIXED 2026-08-27 on the owner's explicit instruction — **still wants a demo session before it is trusted live**
**Found:** 2026-08-26, while writing coverage tests for `core_bot_panel.py`
**Touches money:** **yes.** Immediate Market Entry decides whether a signal is
entered at market straight away instead of resting for its zone.
**Severity:** live, and it fails in the unsafe direction

## The bug

`backend/src/services/positions/core_bot_panel.py`, two places:

```python
640:   ime = "ON" if rs.get("ime_enabled") else "OFF"
1476:  on = not bool(rs.get("ime_enabled"))
       return Screen(await (ctx._cmd_ime_on([]) if on else ctx._cmd_ime_off([])), mode="send")
```

There is no `ime_enabled` key in risk settings. The column is
`immediate_market_entry`, which is what every other call site in the codebase
reads — `services/signals/scan_messages.py:224` among them. Verified against a
freshly migrated database:

```
dpm_enabled              present=True   value=0
ime_enabled              present=False  value=None
immediate_market_entry   present=True   value=0
```

So `.get()` returns `None` every time, `on = not bool(None)` is always `True`, and:

- the **System menu always displays "IME: OFF"**, whatever the real setting is;
- the **button always calls `_cmd_ime_on`** — from Telegram, Immediate Market
  Entry can be switched on and **never switched off**.

The neighbouring DPM toggle is fine: `dpm_enabled` is a real key.

## Why this matters more than it looks

This codebase has already had "IME cannot be turned off" once, from a different
cause. `tests/conftest.py` records it:

> the gd2 one silently re-enabled Immediate Market Entry within seconds of the
> user turning it off, making it impossible to disable at all

That one was a backfill re-running on every boot. This is a misspelled key. Same
user-visible outcome, and the same direction of failure — a control that only
ever moves toward entering trades sooner.

## The fix

Read `immediate_market_entry` in both places. There is no ambiguity about the
name: it is the key the rest of the app uses.

It is one word in two lines, and it is still not something to change unattended,
because it changes when orders are placed at market — `docs/system/rules/
10-golden-rules.md` and the CLAUDE.md "stop and ask" list both cover it. It wants
the owner's sign-off and a demo session, like everything else on that list.

## What is already in place

`tests/core/test_bot_panel_actions.py` holds both halves:

- `test_the_ime_button_reads_a_key_that_does_not_exist` — pins the broken
  behaviour as it stands today, so nobody "fixes" it by accident without noticing.
- `test_the_ime_button_should_toggle_against_the_real_setting` — the intended
  behaviour, marked `xfail(strict=True)`. When the key is fixed this becomes an
  XPASS and fails the suite, which is the prompt to delete the marker and the
  broken-behaviour test above it.

## Also worth checking while you are in there

Whether anything else reads a settings key that does not exist. The same
one-line sweep that found this (`get_risk_settings()` vs `.get(...)` call sites)
would answer it, and this is the third silent-key bug found in two days —
see [010](010-test-panel-reset-params-nameerror.md) and
[011](011-signal-generator-analysis-nameerror.md).

---

## Fixed

Both reads now use `immediate_market_entry`. `core_bot_panel.py:643` (the System
menu's status line) and `:1479` (the toggle).

Verified end to end against a real migrated database, not just through the fakes:

```
IME currently ON  -> button calls: ime_off
IME currently OFF -> button calls: ime_on
```

The tests moved with it. `test_the_ime_button_reads_a_key_that_does_not_exist`
is gone, the `xfail(strict=True)` marker is gone, and what remains asserts both
directions of the toggle plus both states of the status line —
`test_the_ime_button_toggles_against_the_current_setting` and
`test_the_system_menu_reports_the_real_ime_state`. Reverting the one-word change
turns both red, which was checked.

The DPM toggle is asserted alongside it now too. It was never broken, but the
two sit next to each other on the same screen and read the same way, so they are
worth keeping legible together.

**What this still needs.** This changes when orders are placed at market. It has
not been exercised against a broker, demo or live —
`docs/system/rules/20-trading-safety.md` and the CLAUDE.md "stop and ask" list
both want a demo session for that, and the instruction to fix it is not the same
thing as having run it. Before trusting it: on demo, open the Telegram panel with
IME genuinely ON, press the button, and confirm the setting actually goes to 0
and the label flips — the failure this repairs is precisely one where the button
appeared to work and did the opposite.

