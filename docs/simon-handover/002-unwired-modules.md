# Q002 — Four built-but-never-connected features: keep, connect, or remove?

**Who answers:** Simon (the first two are yours; the last two Darren has
already leaned on — just confirm unless you know better).
**Status:** an audit found four pieces of the app that were written but never
plugged in. Nothing was deleted — removing an intended feature by accident
would be worse than carrying it — so each one needs a call.

How to answer: write on each **ANSWER:** line. *"A"* is a complete answer;
add anything you remember about why it exists.

---

## 1 of 4 — Automatic rule learning (`rule_generator`)

When the AI rescues a signal the normal reader couldn't parse and you
approve it, this piece was meant to *learn a rule* from it so the same
message shape parses automatically next time. A similarly-named piece
(`ai_rule_generator`) IS connected — this one may be an older duplicate or
the intended replacement that never got plugged in.

- **A. Investigate first: work out which of the two is the real one, then
  wire or remove accordingly** *(recommended)*
- **B. Remove this one — the connected one is the keeper**
- **C. You remember choosing this feature — connect it**

**ANSWER:**


---

## 2 of 4 — The licence checker's phone-home client (`licence/client`)

A small piece that would let installed copies verify their licence against
your server over the internet. Never connected; the licence currently
verifies locally. This decision ties into the bigger licence-security rework
on the future roadmap.

- **A. Leave it parked; decide when the licence rework happens**
  *(recommended)*
- **B. Remove it**
- **C. Connect it now**

**ANSWER:**


---

## 3 of 4 — The breakout back-tester (`breakout_signal/backtest`)

A tool for testing breakout-strategy tweaks against history *before* they
touch live trading. Runs by hand; not reachable from the app's screens.

- **A. Keep it as a hand-run safety tool** *(Darren's lean — a pre-live
  test harness is worth having)*
- **B. Remove it**
- **C. Give it a button in the app eventually**

**ANSWER:**


---

## 4 of 4 — Password protection on the Bounce/TEST module (`test_signal/auth`)

A password gate for one tab, written and then disconnected. Only you know
whether that was deliberate.

- **A. It was dropped on purpose — remove it** 
- **B. It should still be there — reconnect it**
- **C. Don't remember — leave it parked** *(current default)*

**ANSWER:**

