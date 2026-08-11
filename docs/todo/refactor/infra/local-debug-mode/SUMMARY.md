# Local debug mode — the changes, in plain English

For Simon. A per-area breakdown of what's changing and why — no jargon, no code. Numbers marked
*(starting value)* are proposals, not decisions. Full detail lives in the task files.

Why any of this: Darren has been restructuring the app's internals, but he has no MT5 account,
no Telegram keys and no licence — so until now he literally could not switch the app on to check
his own work. This pack gives the app a "debug mode" that runs the whole system on **pretend
data with no internet and no keys**, so the restructure gets properly exercised before it comes
back to you.

---

## 1. Debug mode switch

**Problem:** the app cannot start at all without your credentials.

| Change | Today | After |
|---|---|---|
| New setting `debug_mode` | doesn't exist | off by default; when on, every outside connection is replaced by a built-in pretend version |
| Your setup | — | **completely unchanged unless the switch is turned on** |

## 2. Pretend broker (MT5)

**Problem:** every price and every order requires the live MT5 terminal.

| Change | Today | After |
|---|---|---|
| Prices | live MT5 feed | a built-in simulated gold price stream (scripted or random) |
| Orders | real MT5 orders | pretend orders filled instantly inside the app; a pretend balance tracks wins/losses |
| Your live/demo data | — | untouched — debug mode uses its own separate database file |

## 3. Pretend Telegram

**Problem:** signals arrive only through your Telegram account; alerts need your bot.

| Change | Today | After |
|---|---|---|
| Incoming signals | your Telegram group | scripted example signal messages fed through the exact same reading/parsing code |
| Outgoing alerts | your Telegram bot | switched off in debug mode (shown in the app log instead) |

## 4. Pretend news, AI and email

| Change | Today | After |
|---|---|---|
| News calendar | fetched from the internet | fixed sample events in debug mode |
| AI commentary | Anthropic/DeepSeek with your key | canned responses in debug mode |
| Email notifications | Resend/Mailjet/Gmail | switched off in debug mode |

## 5. Licence

**Problem:** the app refuses to start without a valid licence key, which Darren doesn't have.

We will **not** weaken or skip the licence check — the rules forbid that. Instead Darren would
generate a short-lived key for his own machine using the same generator your admin server uses,
and the normal check passes honestly. **This one needs your explicit OK** (QUESTIONS.md, item 1),
because it documents that the generator's secret lives in the code you shared.

## 6. A real login for the dashboard

**Problem:** today the app's web dashboard has no password at all — anyone who can reach port
8888 sees and controls everything. (This ships to you too, not just debug mode.)

| Change | Today | After |
|---|---|---|
| Opening the dashboard | loads straight in | asks for username + password (you set them on first run) |

## 7. The banner

When debug mode is on, a bright full-width banner sits at the top of every screen: **"DEBUG MODE
— simulated data, no real orders"** *(wording — starting value)*. There is no way to be in debug
mode without seeing it.

## 8. Automatic end-to-end tests

New tests boot the whole app in debug mode and walk a signal from "message arrives" → "order
placed" → "stop-loss managed" → "closed and recorded", with no internet. These run in the normal
test suite, so future changes get checked against the full pipeline automatically.

---

## Does this touch money?

Almost nothing here changes how orders are placed, closed or sized. The one exception: the small
piece of code that **chooses which broker connection to use** gains a third option ("the pretend
one"). That choice-point edit counts as money-touching under the house rules, so it gets the
safe-change protocol, your sign-off, and a demo session on your machine before live use.

## What stays exactly as it is

- All trading logic: strategies, sizing, stop management, the close path — byte-identical.
- Your config and data files, and the app's behaviour with debug mode off.
- The licence check itself.

---

*Scope:* everything above ships as one pack. **Not doing:** backtesting on fake data, multi-user
accounts, the double-order/reconciliation fixes (those are SPEC-002/003), any of the 2026-08-08
review findings.
