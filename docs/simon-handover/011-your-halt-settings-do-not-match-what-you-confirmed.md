# Your protective limits are not set to the numbers you confirmed

**Status:** needs you. This is a settings question on your own account, so I
have not touched it.
**Found:** 2026-08-29, doing stage3/050.
**Why it matters:** these are the limits that stop trading after a bad run.

## What you confirmed

[001-trading-defaults.md](001-trading-defaults.md), 25 August:

> **A — confirmed. 3% daily loss, 10% drawdown from peak, 3 losing trades in a
> row.**

## What your demo account is actually set to

Read from `forex_trader_demo.db` this evening:

| Setting | Yours | You confirmed |
|---|---|---|
| Risk governor enabled | **OFF** | on (implied by having limits at all) |
| Max daily loss | **20%** | 3% |
| Max total drawdown | 8% | 10% |
| Circuit breaker enabled | ON | on |
| Consecutive losses | 3 | 3 |
| Give-back guard | OFF | not asked |

## The one that matters most

**The risk governor is off, so your daily-loss limit has never been able to
fire.** That is not a guess — `close_trade.py` already carries the note:

> "this account runs with the governor off, which is why its configured
> daily-loss limit never fired through two losing days"

And even if it were on, it is set to **20%**, not 3%. On a $1,323 account that
is the difference between pausing at about $40 of loss and pausing at about
$265.

## What I changed, and what I did not

**Changed (code):** three places disagreed about the same numbers. The schema
said 8% drawdown, the Settings screen said 8%, and `governor.py` — the code
that actually enforces it — fell back to **20%** for both limits when a key was
missing. The enforcement path had the loosest number of the three. All three now
say 3% and 10%, matching your answer.

**Not changed (your data):** your stored settings. Flipping switches on your
account is your call, not mine, and a code change would not have reached them
anyway — these are values already saved in your database, not absent keys.

## What to do

Settings > Risk, and set them to what you confirmed:

- Risk governor: **on**
- Max daily loss: **3%**
- Max total drawdown: **10%**

Then trip it once on demo to watch it work. That is the killer demo for
stage3/050 and it needs a live session anyway.

**ANSWER (do you want these three set as above?):**


---

## ANSWERED, 2026-09-01

> **"I will do it in the UI, keep it as is."**

So: **no code change.** The three sources now agree on 3% / 10% and the
enforcement path no longer carries the loosest number of the three — that part
was fixed on 2026-08-29 and stands. Changing the values on the account is
Simon's, through Settings.

**Still to do on the account, by Simon:** turn the risk governor ON, set max
daily loss to 3%, set max drawdown to 10%. Until the governor is on, the
daily-loss limit cannot fire regardless of what it is set to — that is the one
that matters, and it is why demo 5 in the runbook shows nothing until it is
done.
