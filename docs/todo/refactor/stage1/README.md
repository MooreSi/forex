# Review remediation — August 2026 system review

**Spec:** the money-path anchors (SPEC-002/003) and the phase-1 money tasks now live in
**[stage 3](../stage3/README.md)** (extracted 2026-08-11, Simon-gated); phases 2–4 tasks carry their own scope
**Status:** phases 1–2 largely done; phases 3–4 folded into [stage 2](../stage2/README.md)
**Domain:** stage1 (cross-cutting remediation — the Aug-08 review)
**Touches money:** the money-path work moved to [stage 3](../stage3/README.md); phase2 tasks 030/040 (deferred within 050) are the only money-adjacent items left here.
**Created:** 2026-08-08

## 👋 Picking this up (agents start here)

1. **Read the rules first** — [CLAUDE.md](../../../../CLAUDE.md) and
   [docs/system/rules/10-golden-rules.md](../../../system/rules/10-golden-rules.md). This app places real orders with
   real money.
2. **Read the plan** — the anchor specs above for the money-path
   what-must-NOT-change; this hub for the index + decisions;
   [REVIEW.md](REVIEW.md) for the evidence (the six review reports).
3. **Check [PROGRESS.md](PROGRESS.md)** — the shared status log. See what's done / in progress / free.
4. **Claim your task** in PROGRESS.md: set its row to `in progress`, add your name + date under Owner.
5. **Do the work** from the task file (`0N0-*.md`) — tests first, watch them fail, then implement.
6. **Update PROGRESS.md** as you go — `done` (with commit) or `blocked` (say why).

Gates: `/safe-change` before touching anything that can move money · `/add-tunable` when a number
should be user-editable · `/split-file` if the target file is over 800 lines · `python -m tools.checks all`
before every commit.

## The goal — "Safe to run, clean to build on"

Darren's target (2026-08-10): **everything fixed up so the app can be run
locally with confidence.** Concretely, done means:

1. **It runs clean, locally** — boots on 127.0.0.1, demo mode, no network
   exposure; the safety net is real (gates that bite, migrations that can't
   half-apply, a DB backup, blocking calls off the event loop).
2. **Structural debt paid down** — dead code gone, giant files split, the
   frontend restructure moving, so new features aren't fighting the codebase.
3. **Every money-path fix specced, test-planned and staged** — ready for the
   brother to sign off and watch on a demo terminal in one focused session,
   nothing half-applied.
4. **The [questions queue](../../../simon-handover) is complete** so his review is a
   single pass.

Key line: running locally on demo *already works today*. This pack makes it
**trustworthy** (green means green; an upgrade won't corrupt the DB; a crash
won't leave the books lying). The changes that make it safe to run **live**
(order dedup, reconciliation) are the brother's sign-off items; everything else
is finishable now.

## What we're building & why

The 2026-08-08 full system review ([docs/reviews/2026-08-08/](../../../reviews/2026-08-08))
found the architecture fundamentally sound but the system **not safe to expand**:
one signal can fire two live orders through three timeout/retry gaps; broker
actions and DB records are dual-written with no reconciliation; protective
halts default OFF; and two of the guardrail gates are silently dead (the orphan
detector scans a deleted directory — the exact failure CLAUDE.md warns about,
recurred).

This pack fixes the review findings in strict priority order before feature
expansion resumes. Phase 1 stops active money-loss risk. Phase 2 makes the
safety net real (gates that actually gate, migrations, atomic risk checks,
backups). Phase 3 pays down the expansion tax (dead code, engine duplication,
oversized files). Phase 4 is hygiene (CI, test layout, licensing).

The phase ordering is deliberate: **guardrails are repaired (phase 2, task 010)
before the dead-code deletion (phase 3) they are supposed to police**, and every
money-path fix lands under an anchor spec with a demo session.

## What must NOT change

- The frozen close path (`close_trade`, `record_close`, `_make_close_trade_ctx`,
  `partial_close_trade`) — called, never copied or reshaped. See both anchor specs.
- The atomic signal claim and miss-streak=2 close confirmation — good designs, keep.
- The four layer contracts stay at zero violations throughout.
- `max_open_trades=1` default does not move.
- No ratchet baseline is lowered to get green; gates get *stricter* here, never looser.
- `docs/todo/refactor/stage0/` untouched.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live shared status log |
| [QUESTIONS.md](QUESTIONS.md) | Decisions to confirm before/while building |
| [SUMMARY.md](SUMMARY.md) | Plain-English digest of every change (owner-facing) |
| [REVIEW.md](REVIEW.md) | Evidence — pointers into the six review reports |
| [phase1-stop-the-bleeding/](phase1-stop-the-bleeding/README.md) | P0: localhost bind (done). Money-path Criticals → [stage 3](../stage3/README.md) |
| [phase2-safety-net/](phase2-safety-net/README.md) | P1: gates, migrations, atomic risk checks, backups |
| [phase3-expansion-tax/](phase3-expansion-tax/README.md) | P2: dead code, duplication, oversized files, coverage |
| [phase4-hygiene/](phase4-hygiene/README.md) | P3: CI, test layout, licensing, docs of what shipped |

## Roadmap

| Phase | Task | Depends on | Money | Ships with |
|---|---|---|---|---|
| 1 | 050 bind dashboard to localhost (done) | — | no | — |
| 1 | order-send dedup / timeout / reconciliation / no-db-close / halts | — | YES | → **[stage 3](../stage3/README.md)** (Simon-gated) |
| 2 | 010 guardrail gates fail closed | phase 1 | no | — |
| 2 | 020 schema migrations framework | — | no | — |
| 2 | 030 risk-gate atomicity | phase 1 | YES | — |
| 2 | 040 record_close idempotency guard | phase 1 | YES | — |
| 2 | 050 DB connection config, FK-safe deletes, backups | 020 | no | — |
| 2 | 060 news-calendar off the event loop | — | no | — |
| 2 | 070 update-channel: disable until signed | — | no | — |
| 3 | 010 delete dead code | phase2 010 | no | — |
| 3 | 020 consolidate engine shared code | 010 | no | — |
| 3 | 030 execute the 001 frontend restructure pack | — | no* | — |
| 3 | 040 split database.py, retire re-export hub | — | no | — |
| 3 | 050 frontend exception + timer hygiene | 030 | no | — |
| 3 | 060 money-path coverage floors | phase2 010 | no | — |
| 4 | 010 CI job for tools.checks | phase2 010 | no | — |
| 4 | 020 test layout consolidation | — | no | — |
| 4 | 030 licence asymmetric signing | — | no | — |
| 4 | 040 docs of what shipped | all shipped tasks | no | — |

\* task 3/030 delegates to the existing pack at
[docs/todo/refactor/frontend/restructure/](../frontend/restructure/) — its own task 1/020
is money-touching and governed there. This pack does not fork it.

## Decisions locked with the user (2026-08-08)

| Decision | Choice | Source |
|---|---|---|
| Pack layout | Phased by priority tier (P0→P3), not per-topic dirs | user |
| Deployment topology | Single install, localhost-only today | user |
| Consequence: dashboard fix | Bind to 127.0.0.1 now; full auth deferred until networked | user topology answer |
| Consequence: update channel | Downgraded P0→phase 2; simplest fix is disable-until-signed | user topology answer |
| Consequence: cluster sync conflict handling | Out of scope for this pack | user topology answer |
| Money-path anchoring | Anchor specs written first (SPEC-002, SPEC-003) | user |
| Guardrails before dead-code deletion | Phase 2 gate repair gates phase 3 deletion | review (testing H1) |

### Provisional decisions (2026-08-10) — recommendations adopted, brother's confirmation pending

Darren adopted all six QUESTIONS.md recommendations so work can proceed; the final decision-maker
(his brother) has not yet reviewed them. Check QUESTIONS.md for overrides before implementing the
consuming task.

| Decision | Provisional choice | Consumed by |
|---|---|---|
| Trade-id transport | Both order comment and magic number | 1/010 |
| Reconciliation mode | Report-only first week, then repair; every 60s | 1/030 |
| Halt defaults | 3% daily loss / 10% drawdown / 3 consecutive losses; pause opens only | 1/060 |
| Backups | Daily snapshot to second local folder, keep 30 | 2/050 |
| Update channel | Disable now, decide later | 2/070 |
| No-id broker positions | Watch only (`recovered-manual`) | 1/030 |

## Building blocks we reuse (do not rebuild)

| Need | Existing code |
|---|---|
| Guarded close recording | `backend/src/runtime.py:420-506` — frozen-path wrappers; reconciliation routes through these |
| Broker queries (positions/deals) | `backend/src/services/broker/` — read-only calls reused by dedup + reconciliation |
| Close-confirmation discipline | miss-streak=2 logic in `positions/` — complement, don't replace |
| Gate self-test doctrine | `tests/refactor/` negative-control pattern — extend to the repaired gates |
| MT5 test fakes + Popen guard | existing test fixtures — every new test rides these |
| Settings/tunables plumbing | `/add-tunable` path — reconciliation interval, halt thresholds |

## Out of scope

- Cluster-sync conflict detection / multi-node reconciliation — single-node
  deployment; revisit when a second node exists (future pack under a
  `cluster` domain).
- Full dashboard authentication (login, sessions) — deferred until the app is
  networked; phase1/050 is the localhost bind only.
- Any strategy/signal-quality change — this pack is safety + structure only.
- The frontend restructure content itself — lives in its own pack
  ([docs/todo/refactor/frontend/restructure/](../frontend/restructure/)); phase3/030
  only unblocks and sequences it.

## Open questions

Full write-ups in [QUESTIONS.md](QUESTIONS.md); short list:

- Trade-id transport: comment, magic, or both (default: both)
- Reconciliation interval + report-only first release (default: 60s, report-only ON)
- Protective-halt default thresholds (daily loss %, drawdown %)
- Backup destination + cadence for the live DB
- Kill vs harden the auto-update channel long-term
- Adoption policy for broker positions with no trade id (manual trades)
