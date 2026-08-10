# Review remediation — decisions to confirm

Plain-English choices to settle before building. Each has a **recommendation** — you can say "go with
the recommendations" and only change what you disagree with. Numbers are starting points, not decided
values (anything you should be able to change later goes through `/add-tunable`). No jargon.

Answer inline (write `ANSWER:` under each). Answered items stay, annotated — don't delete them.

> **2026-08-10 — all six answered with the recommendations, provisionally.** Darren adopted every
> recommended option so work can proceed; the final decision-maker is his brother, who has not yet
> reviewed these. Any answer below may be overridden by him **before the task that consumes it is
> implemented** — check for an override before building 1/010 (Q1), 1/030 (Q2, Q6), 1/060 (Q3),
> 2/050 (Q4), 2/070 (Q5). An already-shipped default his answer changes becomes a follow-up task,
> not a silent edit.

## The decisions (quick list)
1. How does an order carry its id at the broker — comment, magic number, or both?
2. Reconciliation: start in report-only mode, and how often does it run?
3. Protective halts: what are the default limits when they switch on?
4. Where do database backups go, and how often?
5. The auto-update channel: kill it or harden it?
6. A broker position with no id (e.g. a manual trade): manage it or just watch it?

---

## 1. How does an order carry its id at the broker?
Dedup only works if the id survives at the broker. Some brokers strip or rewrite order comments.

- **Both comment and magic (Recommended)** — comment is human-readable in the MT5 terminal; the
  magic number survives comment-stripping. Redundancy costs nothing.
- **Comment only** — simpler, but one broker-side rewrite silently breaks dedup.
- **Magic only** — robust but invisible to a human scanning the terminal.

ANSWER: recommended — both comment and magic. (2026-08-10, provisional per note above.)

## 2. Reconciliation: report-only first, and how often?
The reconciler repairs DB records from broker truth. A bug in a repairer could mis-record trades, so
the first release can log what it *would* do without doing it.

- **Report-only ON for the first week, repair after; every 60s (Recommended)** — you read the
  reports, confirm they're sane, then flip repair on. 60s is fast enough to catch orphans before the
  next signal.
- **Repair from day one** — faster protection, no observation period.
- **Startup-only, no periodic run** — cheaper, but a mid-session crash leaves an orphan unmanaged
  until next restart.

ANSWER: recommended — report-only ON for the first week, then repair; every 60s. (2026-08-10, provisional per note above.)

## 3. Protective halts: default limits when they switch on?
Daily-loss cap, drawdown halt and the circuit breaker currently default OFF. Phase 1 turns them ON
by default; they need numbers. These become tunables — starting values, not forever values.

- **Conservative start (Recommended)** — daily loss cap 3% of balance, drawdown halt 10%, circuit
  breaker after 3 consecutive losses. Halts pause new opens only; never auto-closes anything.
- **Looser** — 5% / 15% / 5 losses.
- **You name the numbers** — write them under ANSWER.

ANSWER: recommended — conservative start: daily loss cap 3%, drawdown halt 10%, breaker after 3
consecutive losses; pause new opens only. (2026-08-10, provisional per note above — these numbers
especially warrant the brother's eye before 1/060 ships; they are tunables afterwards.)

## 4. Where do backups go, and how often?
The live-money books are one SQLite file on one disk. Task 2/050 adds a backup.

- **Daily snapshot to a second local folder + keep 30 (Recommended)** — simple, offline, no new
  dependencies; you can add off-machine copies later.
- **On every app shutdown** — cheaper, but a machine that never restarts never backs up.
- **Off-machine (cloud/NAS) from day one** — better disaster story, needs a destination from you.

ANSWER: recommended — daily snapshot to a second local folder, keep 30. (2026-08-10, provisional
per note above.)

## 5. The auto-update channel: kill or harden?
It is currently an unauthenticated code-execution path. You said the install is single-node
localhost, so it may not even be in use. Task 2/070 disables it by default either way.

- **Disable now, decide later (Recommended)** — one config default. If you distribute the installer
  to others later, we do the full job then: signed updates, pinned certs, no LAN discovery.
- **Harden now** — signing + pinning is meaningful work (days) that only pays off if updates are
  actually being pushed.
- **Remove the code entirely** — cleanest, but destroys the feature if the big vision needs it.

ANSWER: recommended — disable now, decide later. (2026-08-10, provisional per note above.)

## 6. A broker position with no id: manage or watch?
Today the importer auto-adopts any broker position into active management (review risk H6) — a
manual trade you place yourself would get its SL moved by the bot.

- **Watch only (Recommended)** — record it as `recovered-manual`, show it in the UI, never touch its
  SL/TP or close it. You stay in charge of your own manual trades.
- **Adopt fully (current behaviour)** — the bot manages everything it sees.
- **Ask per position** — a UI prompt on discovery; more work, only worth it if manual trading is
  frequent.

ANSWER: recommended — watch only (`recovered-manual`: shown in UI, never touched). (2026-08-10,
provisional per note above.)

---

## Quick-confirm checklist
- [x] 1 — id transport? → both comment and magic (provisional)
- [x] 2 — report-only first + interval? → report-only 1 week, then repair; 60s (provisional)
- [x] 3 — halt numbers? → 3% daily / 10% drawdown / 3 losses (provisional)
- [x] 4 — backup destination + cadence? → daily local snapshot, keep 30 (provisional)
- [x] 5 — update channel: disable / harden / remove? → disable now (provisional)
- [x] 6 — manual positions: watch or manage? → watch only (provisional)
- [x] Anything here that changes order placement, closing or sizing is flagged as money-touching in
      the README and its task file.

*Once answered: record each choice in the README's "Decisions locked" table with the date, and
annotate the question above rather than deleting it.*
