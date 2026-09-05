# Q001 — Six trading & operations defaults

**Who answers:** Simon.
**Status:** **ANSWERED 2026-08-25** — all six confirmed as the standing
defaults, with item 5 later amended (see the amendment below).

Working defaults were chosen on 2026-08-10 so the build could
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

**ANSWER:** A — confirmed. Tag both the order comment and the magic number.
(Simon, 2026-08-25)


---

## 2 of 6 — Reconciliation: how cautious to start, and how often?

A checker will compare what MetaTrader says you hold against what the app's
database says, and flag mismatches. Example: the app crashes right after an
order fills — on restart the checker spots the position the database missed.

- **A. First week report-only (it tells you, touches nothing), then switch
  to repair mode; check every 60 seconds** *(current default)*
- **B. Repair from day one**
- **C. Report-only permanently until you say otherwise**

**ANSWER:** A — confirmed. Report-only for the first week, then switch to repair
mode; check every 60 seconds. A week of watching it be right before it is allowed
to change anything. (Simon, 2026-08-25)


---

## 3 of 6 — The protective limits (the numbers that pause trading)

When a limit is hit the app **pauses opening new trades** — it never closes
what's already open. Example with default numbers on a £1,000 account: lose
£30 in a day → no new trades until tomorrow.

- **A. 3% daily loss · 10% drawdown from peak · 3 losing trades in a row**
  *(current default)*
- **B. Your own numbers** — write them: daily-loss %, drawdown %, losses-in-a-row

**ANSWER:** A — confirmed. 3% daily loss, 10% drawdown from peak, 3 losing
trades in a row. Retune later from real data rather than guessing now.
(Simon, 2026-08-25)

> **Note added 2026-08-25 during the upstream merge.** The live app has since
> gained a **seventh** protective limit that this question did not cover: a
> *give-back guard* that stops the day once a share of the day's profit has been
> handed back. It ships **off**, arms above **$50** of day profit and triggers at
> **40%** given back (`giveback_guard_enabled` / `giveback_arm_usd` /
> `giveback_pct`). It arrives with the merge of `MooreSi/forex`. Simon has not
> been asked to confirm those three numbers yet — raise them at the Part B
> sitting alongside the B5 protective-halts demo.


---

## 4 of 6 — Backups: where and how often?

- **A. Automatic daily snapshot of the database to a second folder on the
  same machine, keeping the last 30 days** *(current default — already
  running)*
- **B. Different schedule or location** — say what you'd prefer (e.g. also
  copy to a USB drive / cloud folder weekly)

**ANSWER:** A — confirmed. Automatic daily snapshot to a second folder on the
same machine, keeping the last 30 days. (Simon, 2026-08-25)


---

## 5 of 6 — The remote auto-update channel

The app had a channel that could receive and apply pushed updates over the
network. It had no security on it, so it has been **switched off by
default** (turning it on prints a loud warning).

- **A. Leave it off; decide about securing it later** *(current default)*
- **B. Remove the feature entirely**
- **C. Prioritise securing it (signed updates) so it can come back**

**ANSWER:** A — confirmed. Leave it off; decide about securing it later.
(Simon, 2026-08-25)

> ### AMENDED 2026-08-25 — the original answer is superseded
>
> Answer A was given before Q005 #3 established that **Simon actively uses the
> admin console**: to see which clients are online and for how long, to view and
> revoke licence-key permissions, and to trigger updates. Leaving the channel off
> would break something he relies on, so A is the wrong answer to the question as
> it was framed.
>
> **REVISED ANSWER: default the remote-admin client ON after the upstream merge,
> and rewrite the warning text. (Simon, 2026-08-25)**
>
> **Why the original "off" reason has largely evaporated.** The justification —
> still quoted verbatim in the warning at `backend/src/app.py:193`, "will APPLY
> PUSHED CODE, with no signature check" — describes a path upstream has since
> deleted. Commit `0815cc6` (2026-08-02) removed the zip-streaming protocol
> entirely and replaced it with a single `MSG_GIT_UPDATE` trigger: the admin's
> button now only asks a connected client to run its own git fetch from GitHub.
> Commit `062b2be` separately fixed LAN discovery, which had accepted *any* host
> on the subnet with port 8443 open (a router or NAS answered the probe as
> readily as the real server), by requiring a completed WebSocket handshake
> before a candidate is accepted.
>
> **What is still genuinely unsafe, and must be recorded honestly.** The TLS
> connection runs `CERT_NONE` with `check_hostname = False` (`remote/tls.py:93`)
> and the client does **not** pin the server certificate — upstream `062b2be`
> states plainly that it cannot, because the fingerprint file only ever exists on
> the server machine. An attacker on the network path can therefore still
> impersonate the admin server. What they gain is much smaller than before: the
> worst trigger available is a git pull from Simon's own repository, not
> arbitrary code execution.
>
> **Work this authorises** (after the merge, as its own commit):
> 1. Flip `remote_admin_client_enabled` to default `true` in
>    `backend/src/app.py:190`.
> 2. Rewrite the `app.py:193` warning to describe the *real* remaining risk
>    (unverified TLS, no cert pinning) instead of the deleted code-push path. A
>    warning that describes a risk which no longer exists trains people to ignore
>    warnings.
> 3. Update `tests/controllers/test_update_client_disabled.py`, which asserts the
>    old default, and rename it to match the new behaviour.
> 4. Raise **certificate pinning** as a tracked follow-up — it is now the last
>    unauthenticated link in this channel.
>
> **All four are done. (Added 2026-09-05.)** Item 4's follow-up became
> `docs/todo/security/010`, and was closed on 2026-09-02 by the wider TLS work
> in [../todo/bugs/014](../todo/bugs/014-sync-and-licence-tls-are-unauthenticated.md):
> a private CA for the internet path and trust-on-first-use for the LAN, both
> checked before the licence token is sent. **Item 2's warning had to be
> rewritten a second time** — the version written here correctly described
> "unverified TLS, no cert pinning", and that description expired the day the
> pinning landed. It now names TOFU's first LAN connection, which is the only
> exposure left. The paragraph above it is the reason: a warning describing a
> risk which no longer exists trains people to ignore warnings, and this one had
> three days to do exactly that.
>
> **Stale document to fix:** `docs/todo/refactor/stage1/phase2-safety-net/
> 070-update-channel-disable.md` still reads `Status: not started` although the
> work shipped (the flag, the warning and its tests all exist). Its premise line,
> "Owner confirms single-node localhost deployment — nothing legitimate currently
> needs this channel", is now known to be false.


---

## 6 of 6 — A broker position the app doesn't recognise

If reconciliation finds a position at MetaTrader with no matching record —
e.g. a trade you placed manually in MT5 yourself — what should the app do?

- **A. Watch it only: show it, track its profit, never touch it**
  *(current default — safest)*
- **B. Adopt it fully: manage its stop/targets like its own trades**
- **C. Ask you each time**

**ANSWER:** A — confirmed. Watch it only: show it, track its profit, never
touch it. Manual MT5 trades stay Simon's; the app still counts them toward
exposure and the risk limits, but never moves a stop or closes one.
(Simon, 2026-08-25)


---

*Confirming these numbers is a decision. The safety features that use them
(de-duplication, reconciliation, the limits) still get built test-first and
demonstrated to you on your demo account before they switch on — that's the
session-agenda Part B.*
