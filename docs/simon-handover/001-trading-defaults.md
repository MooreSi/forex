# Q001 — Six trading & operations defaults

**Who answers:** Simon.
**Status:** working defaults were chosen on 2026-08-10 so the build could
continue. Nothing here has made the app trade more aggressively — every
default is watch-only, off-by-default, or stricter than before. You are
confirming or changing them.

How to answer: read each question, then write on its **ANSWER:** line.
*"A"* (or *"keep it"*) is a complete answer. Add anything in your own words.

---

## 1 of 6 — How should an order carry its ID at the broker?

Every order the app places gets tagged so it can recognise its own positions
at MetaTrader later (that's what makes de-duplication and reconciliation
possible).

- **A. Tag both the order comment AND the magic number** *(current default —
  belt and braces; survives brokers that blank one of the two)*
- **B. Comment only**
- **C. Magic number only**

**ANSWER:**


---

## 2 of 6 — Reconciliation: how cautious to start, and how often?

A checker will compare what MetaTrader says you hold against what the app's
database says, and flag mismatches. Example: the app crashes right after an
order fills — on restart the checker spots the position the database missed.

- **A. First week report-only (it tells you, touches nothing), then switch
  to repair mode; check every 60 seconds** *(current default)*
- **B. Repair from day one**
- **C. Report-only permanently until you say otherwise**

**ANSWER:**


---

## 3 of 6 — The protective limits (the numbers that pause trading)

When a limit is hit the app **pauses opening new trades** — it never closes
what's already open. Example with default numbers on a £1,000 account: lose
£30 in a day → no new trades until tomorrow.

- **A. 3% daily loss · 10% drawdown from peak · 3 losing trades in a row**
  *(current default)*
- **B. Your own numbers** — write them: daily-loss %, drawdown %, losses-in-a-row

**ANSWER:**


---

## 4 of 6 — Backups: where and how often?

- **A. Automatic daily snapshot of the database to a second folder on the
  same machine, keeping the last 30 days** *(current default — already
  running)*
- **B. Different schedule or location** — say what you'd prefer (e.g. also
  copy to a USB drive / cloud folder weekly)

**ANSWER:**


---

## 5 of 6 — The remote auto-update channel

The app had a channel that could receive and apply pushed updates over the
network. It had no security on it, so it has been **switched off by
default** (turning it on prints a loud warning).

- **A. Leave it off; decide about securing it later** *(current default)*
- **B. Remove the feature entirely**
- **C. Prioritise securing it (signed updates) so it can come back**

**ANSWER:**


---

## 6 of 6 — A broker position the app doesn't recognise

If reconciliation finds a position at MetaTrader with no matching record —
e.g. a trade you placed manually in MT5 yourself — what should the app do?

- **A. Watch it only: show it, track its profit, never touch it**
  *(current default — safest)*
- **B. Adopt it fully: manage its stop/targets like its own trades**
- **C. Ask you each time**

**ANSWER:**


---

*Confirming these numbers is a decision. The safety features that use them
(de-duplication, reconciliation, the limits) still get built test-first and
demonstrated to you on your demo account before they switch on — that's the
session-agenda Part B.*
