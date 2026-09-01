# Q002 — Four built-but-never-connected features: keep, connect, or remove?

**Who answers:** Simon (the first two are yours; the last two Darren has
already leaned on — just confirm unless you know better).
**Status:** **ANSWERED 2026-08-25** — see the answer table in
[questions.md](questions.md) and the per-item notes below.

An audit found four pieces of the app that were written but never
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

**ANSWER:** B — remove it. (Simon, 2026-08-25)

> **Investigation done 2026-08-25, and it changes the question.** There are not
> two files. There is **one**: `forex_trader/core/ai_rule_generator.py` was
> renamed to `backend/src/services/channels/rule_generator.py` by the refactor,
> byte-for-byte identical (git records it `R100`, commit `a154a54`). The
> "connected one" this question assumed exists does not. Nothing imports or
> calls it **in either repo** — checked `MooreSi/forex` `main` as well as this
> branch. Its two entry points (`generate_rule`, `generate_sl_adjustment_rule`)
> have zero callers; the only mentions anywhere are two stale comments
> (`backend/migrations/schema_sql.py:431`,
> `backend/src/services/signals/parser.py:647`) and a docstring in
> `backend/src/services/cluster/sync/server.py:793`, all naming the old
> filename. The orphan-allowlist reason (`tools/refactor_audit/
> orphan_module_allowlist.json`) was written on the false premise and is wrong.
>
> **Follow-up work this authorises** (separate commit, not part of the upstream
> merge): delete `backend/src/services/channels/rule_generator.py`, drop its
> `orphan_module_allowlist.json` entry, and clear the three stale references
> above. Recoverable from git history if it is ever wanted back.


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

**ANSWER:** A — confirmed. Leave it parked; decide when the licence rework
happens. (Simon, 2026-08-25)

> **Note added 2026-08-25 during the upstream merge.** This area has already
> moved under the question: the live app has since replaced the shared-secret
> licence HMAC with **Ed25519 signing plus Telegram approval**, and added
> auto-healing of old HMAC keys. Revisit this only after that work has landed
> here and been reviewed.


---

## 3 of 4 — The breakout back-tester (`breakout_signal/backtest`)

A tool for testing breakout-strategy tweaks against history *before* they
touch live trading. Runs by hand; not reachable from the app's screens.

- **A. Keep it as a hand-run safety tool** *(Darren's lean — a pre-live
  test harness is worth having)*
- **B. Remove it**
- **C. Give it a button in the app eventually**

**ANSWER:** A — confirmed. Keep it as a hand-run safety tool.
(Simon, 2026-08-25) A way to test a strategy change without risking money is
exactly what this project's rules ask for; having no button does not make it
dead weight.


---

## 4 of 4 — Password protection on the Bounce/TEST module (`test_signal/auth`)

A password gate for one tab, written and then disconnected. Only you know
whether that was deliberate.

- **A. It was dropped on purpose — remove it** 
- **B. It should still be there — reconnect it**
- **C. Don't remember — leave it parked** *(current default)*

**ANSWER:** C — don't remember; leave it parked. (Simon, 2026-08-25)

> Context noted while answering: the module's password helpers
> (`hash_password` / `verify_password` in
> `backend/src/services/test_signal/auth.py`) are still exercised by
> `tests/controllers/test_remote_admin_password.py`, so the file is not inert
> even though the tab's gate is disconnected. Check that test before any future
> deletion.

