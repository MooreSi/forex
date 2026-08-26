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

_Last updated: 2026-08-25._ Answered: **5 of 5 — Part A is closed.**

| # | File | Answer |
|---|---|---|
| 1 | [001-trading-defaults.md](001-trading-defaults.md) | All six confirmed as the standing defaults. **Item 5 later amended** — see below. |
| 2 | [002-unwired-modules.md](002-unwired-modules.md) | 1: **remove** (investigation found one dead file, not two rivals). 2: parked, then resolved by the merge, which deletes it. 3: keep as a hand-run tool. 4: leave parked. |
| 3 | [004-news-no-data-policy.md](004-news-no-data-policy.md) | A — keep trading when news is unknown, log loudly. The upstream fix narrows the blind spot substantially. |
| 4 | [005-fact-finding.md](005-fact-finding.md) | 1: **yes**, logs carry the account number (evidence). 2: secret **never changed**, fixed upstream; 1-3 licences. 3: admin console **is in active use** — assumption was wrong. 4: retention never on. |
| 5 | [007-remaining-approvals.md](007-remaining-approvals.md) | 1: **B** — Simon issues the dev licence from the admin console. 2: **B** — full self-serve is the handover bar. |

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
