# The decision queue — how it works, and the list

**This folder's numbered files are Simon's questions.** Each was hit during
the build; rather than stall, a safe working default was chosen (always one
that keeps trading no more aggressive than before), the app was built to run
on it, and the decision was written down here for you to confirm or change.

**How to answer:** open each numbered file, read it top to bottom, and write
on the **ANSWER:** lines inside it — any text editor works. *"A"* or
*"keep it"* is a complete answer. Answered files stay in place, annotated —
they're the record of what was decided and why.

**One rule to know:** confirming an answer here is a *decision*. The
money-safety changes that use these answers are still built test-first and
demonstrated to you on your **demo** account before they ship — that's
[session-agenda.md](session-agenda.md) Part B, and it never happens without
you watching.

## Simon's questions, in reading order

| # | File | What you're deciding | Effort |
|---|---|---|---|
| 1 | [001-trading-defaults.md](001-trading-defaults.md) | Six trading/operations defaults (order tagging, reconciliation pace, the protective limits, backups, the update channel, unrecognised positions) | ~10 min |
| 2 | [002-unwired-modules.md](002-unwired-modules.md) | Four features that were built but never connected — keep, connect, or remove | ~5 min |
| 3 | [004-news-no-data-policy.md](004-news-no-data-policy.md) | When the news feed is down: keep trading or pause | ~3 min |
| 4 | [005-fact-finding.md](005-fact-finding.md) | Four facts only you know (logs, the licence secret, the update client, retention) | ~5 min |
| 5 | [007-remaining-approvals.md](007-remaining-approvals.md) | The practice-mode licence, and what "handed over" means | ~3 min |

*(There is no 003 or 006 — those were Darren's technical items and live with
the technical docs, not in your folder.)*

## Status

_Last updated: 2026-09-01._ Part A (Q001-Q007): **5 of 5, closed.**
Everything raised since then is in the second table below.

**Q008 onward were raised during the build, and several were answered
verbally in a working session rather than written into their files. That gap
is closed as of 2026-09-01** — where an answer was given out loud, it is
recorded here and in the file, marked as such.

| # | File | Answer |
|---|---|---|
| 1 | [001-trading-defaults.md](001-trading-defaults.md) | All six confirmed as the standing defaults. **Item 5 later amended** — see below. |
| 2 | [002-unwired-modules.md](002-unwired-modules.md) | 1: **remove** (investigation found one dead file, not two rivals). 2: parked, then resolved by the merge, which deletes it. 3: keep as a hand-run tool. 4: leave parked. |
| 3 | [004-news-no-data-policy.md](004-news-no-data-policy.md) | A — keep trading when news is unknown, log loudly. The upstream fix narrows the blind spot substantially. |
| 4 | [005-fact-finding.md](005-fact-finding.md) | 1: **yes**, logs carry the account number (evidence). 2: secret **never changed**, fixed upstream; 1-3 licences. 3: admin console **is in active use** — assumption was wrong. 4: retention never on. |
| 5 | [007-remaining-approvals.md](007-remaining-approvals.md) | 1: **B** — Simon issues the dev licence from the admin console. 2: **B** — full self-serve is the handover bar. |

### Everything raised since Part A

Numbered files 008 onward. "Fixed" means the code change landed with tests;
"decided" means you chose and nothing needed building.

| # | File | State |
|---|---|---|
| 008 | [zone signals and real pending orders](008-zone-signals-and-real-pending-orders.md) | **Answered: A.** |
| 009 | [breached zone: discard or queue](009-breached-zone-discard-or-queue.md) | **Answered 2026-08-31, verbally: "A, and yes realignment on the market path if the option is selected."** Built: `services/trading/entry_realignment.py`, gated on `lk_entry_realignment`. |
| 010 | [session 2026-08-28 evening](010-session-2026-08-28-evening.md) | Session note, not a question. |
| 011 | [your halt settings do not match what you confirmed](011-your-halt-settings-do-not-match-what-you-confirmed.md) | **Answered 2026-09-01: "I will do it in the UI, keep it as is."** Still needs you to set governor on, daily loss 3%, drawdown 10%. |
| 012 | [should a resting order use a trade slot](012-should-a-resting-order-use-a-trade-slot.md) | **Answered 2026-08-31, verbally: A.** |
| 013 | [the five demos runbook](013-the-five-demos-runbook.md) | **Not a question — the session you still owe.** This is the largest remaining item in the whole project. |
| 014 | [a wildcard fingerprint nothing uses](014-a-wildcard-fingerprint-nothing-uses.md) | **Answered 2026-09-01:** no master key; the keygen stays in its own folder. Removed. |
| 015 | [session 2026-08-31](015-session-2026-08-31.md) | Session note. |
| 016 | [the native bridge has the same shape](016-the-native-bridge-has-the-same-shape.md) | **Answered 2026-09-01** — and I had it backwards; corrected in the file. |
| 017 | [which clock is your trading schedule in](017-which-clock-is-your-trading-schedule-in.md) | **Answered and implemented 2026-09-01.** |
| 018 | [the partial close can pay twice](018-the-partial-close-can-pay-twice.md) | **Answered and implemented 2026-09-01.** |
| 019 | [editing a pending signal used the wrong row's numbers](019-editing-a-pending-signal-used-the-wrong-rows-numbers.md) | Fixed. No decision needed. |
| 020 | [out of hours still runs on UTC](020-out-of-hours-still-runs-on-utc.md) | **Partly answered.** The clock question is answered and the offset sync and its UI control are built. **Out of Hours itself is still on UTC and still waiting on you** — moving it changes when a different strategy takes over. |
| 021 | [the day boundary was London's](021-the-day-boundary-was-londons.md) | Fixed. No decision needed. |

### Still open, in one place

_Rewritten 2026-09-11, after a round of answers closed six._

1. **The demos** ([013](013-the-five-demos-runbook.md)) — 10 of 18 passed.
   The eight left need conditions an agent cannot create: a slow EA, a broker
   refusing a close, a position vanishing mid-disconnect, a 20% drawdown, a
   signal on one named channel, a closed schedule window. **The whole
   limit-orders pack is also built, green and undemoed.**
2. **Your halt settings** ([011](011-your-halt-settings-do-not-match-what-you-confirmed.md))
   — yours to set in the UI, ten minutes. The stale drawdown watermark that
   would have halted trading on the first close is fixed (bugs/042); it takes
   effect at the next restart.
3. **One answer on the Out of Hours removal spec**
   ([docs/todo/002](../todo/002-remove-the-out-of-hours-resolver.md) §3) —
   drop the eight database columns, or leave them inert.

**Answered 2026-09-11 and now waiting on build, not on you:**
[041](../todo/bugs/041-a-profitable-harvest-arms-the-circuit-breaker.md) (needs
an EA change and a demo), [023](023-strategies-are-not-ea-templates.md),
[024](024-per-account-databases.md), [027](027-what-should-a-direction-only-message-do.md),
[028](028-sharing-the-engines-learning-with-every-client.md) (and deliberately
not yet).

**Answered 2026-09-11 and needing nothing:**
[030](030-what-sl-parsing-off-costs-per-trade.md) (leave SL parsing off),
[040](../todo/bugs/040-a-resting-order-filling-into-news-is-not-closed.md)
(leave a news-blackout fill alone), the trend gate's manual-order exemptions,
the three give-back numbers in [001](001-trading-defaults.md), and
[020](020-out-of-hours-still-runs-on-utc.md)/
[043](../todo/bugs/043-coming-back-to-an-idle-page-reloads-it.md), both closed.

### Two answers that changed other things

- **Q001 #5 was amended after Q005 #3.** Simon actively uses the admin console,
  so defaulting the remote-admin client to *off* would break it. Revised: default
  it **on** after the merge and rewrite the stale warning. See the amendment on
  [001-trading-defaults.md](001-trading-defaults.md).
- **Q007 #2 raised the bar.** "Handed over" now means self-serve documentation,
  not a guided session. The Part B money-safety demos are still required and
  cannot be waived by this answer.

### Follow-up work these answers authorise

Each is a separate commit, none of it part of the upstream merge itself.

**Status, 2026-08-26: 1, 2, 3, 4, 6, 8 and 9 are done. 5 is written up as a
tracked task ([docs/todo/security/010](../todo/security/010-remote-channel-cert-pinning.md)).
7 belongs to the Part B sitting.**

**Updated 2026-09-05: 5 is DONE too.** It was closed 2026-09-02 under
[bugs/014](../todo/bugs/014-sync-and-licence-tls-are-unauthenticated.md) —
a private CA for the internet path, trust-on-first-use for the LAN, on the
owner's 2026-09-01 decision. The security/010 file said "not started" for three
days after the fact; it now carries the reconciliation. Nothing on this list is
outstanding except 7, which is Simon's sitting.

1. Delete `backend/src/services/channels/rule_generator.py`, its
   `orphan_module_allowlist.json` entry, and three stale references (Q002 #1).
2. Redact the MT5 login number at `mt5_bridge.py:179` and recipient addresses in
   `email_service` before the diagnostics upload is used again (Q005 #1).
3. Default `remote_admin_client_enabled` to `true`, rewrite the warning at
   `backend/src/app.py:193`, update its tests (Q001 #5 amended).
4. Rewrite `tools/generate_debug_licence.py` to *request* rather than mint a
   licence (Q007 #1).
5. Raise **certificate pinning** for the remote channel as a tracked task — after
   the merge it is the last unauthenticated link (Q001 #5 amended).
6. Replace the hardcoded `_FOMC_DATES_2026` list, which goes stale on
   2027-01-01 and silently loses FOMC coverage (Q004).
7. Confirm the three give-back-guard numbers at the Part B sitting (Q001 #3).
8. Update `readiness-checklist.md` and `session-agenda.md` for the raised
   self-serve documentation bar (Q007 #2).
9. Fix the stale `Status: not started` and false premise in
   `docs/todo/refactor/stage1/phase2-safety-net/070-update-channel-disable.md`.
