# Road to handoff — the plan to make this giveable to Simon

**Spec:** none single — this is a program roadmap; each phase anchors on its own review/pack (see below)
**Status:** planning (pre-implementation)
**Domain:** stage2 (release-readiness roadmap)
**Touches money:** only phase 5's one `_make_bridge` wiring task. The money-path (order dedup,
reconciliation, halts) is **[stage 3](../stage3/README.md)** — a separate Simon-gated stage — so
stage 2 is workable today without Simon.
**Created:** 2026-08-11

## 👋 Picking this up (agents start here)

1. **New here? Read [../HANDOFF.md](../HANDOFF.md) first**, then the rules:
   [CLAUDE.md](../../../CLAUDE.md) → [docs/system/rules/10-golden-rules.md](../../system/rules/10-golden-rules.md).
   This app places real orders with real money.
2. **This pack is the master roadmap** to "giveable to Simon". It has its own new work (phases 1–3, 7)
   and it *drives* three existing detailed packs (phases 4–6) rather than duplicating them.
3. **Check [PROGRESS.md](PROGRESS.md)** — the live status log across all phases.
4. **Claim a task** in PROGRESS.md, do it test-first, update PROGRESS.
5. **A question you can't answer** → [../../questions/](../../questions/) (Simon decides). Don't block; don't guess money/policy.

Gates: `/safe-change` before any money task · `/add-tunable` for user-editable numbers · `/split-file`
for files over 800 lines · `python -m tools.checks all` green before every commit.

## What "giveable to Simon" means (the finish line)

Darren is refactoring this for his brother **Simon**, who holds the live account and makes the
trading decisions. Today Darren can boot it in debug mode but said, verbatim, *"it's almost
impossible for me to know what I'm meant to do."* Giveable means all of:

1. **A person who didn't build it can use it** — first-run guidance, plain-language help, sensible
   empty states. (Phase 1.)
2. **The foundations are trustworthy** — schema changes are proper versioned migrations, and the
   test suite actually verifies (no assert-nothing stubs, honest coverage). (Phases 2–3.)
3. **It's maintainable** — the giant frontend files are split and the restructure's layer
   violations are gone. (Phase 4.)
4. **It runs and demos end-to-end offline** — the fake bridge makes debug mode actually tick, with
   an e2e signal→close proof. (Phase 5.)
5. **It's safe with real money** — the order-dedup / reconciliation / halts work is done and
   Simon-signed-off on a demo terminal. (That work is **[stage 3](../stage3/README.md)**.)
6. **The handoff is clean** — HANDOFF.md, a give-to-Simon checklist, current docs, and the open
   decisions parked for Simon. (Phase 7.)

## What must NOT change

- The frozen close path (`close_trade`, `record_close`, `_make_close_trade_ctx`,
  `partial_close_trade`) — called, never reshaped. See [stage 3](../stage3/README.md).
- The four import contracts stay at zero for the enforced-at-zero rules; no ratchet baseline rises
  (coverage or LOC); gates only get stricter.
- Order/close/sizing behaviour is byte-identical except where a phase-6 task deliberately changes it
  under Simon's sign-off.
- `docs/history/` untouched.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live shared status log (all phases) |
| [SUMMARY.md](SUMMARY.md) | Plain-English digest (owner-facing) |
| [QUESTIONS.md](QUESTIONS.md) | Open decisions — routed to Simon / Darren |
| [REVIEW.md](REVIEW.md) | Evidence — the reviews each phase builds on |
| [phase1-usability/](phase1-usability/README.md) | First-run onboarding & comprehension |
| [phase2-proper-migrations/](phase2-proper-migrations/README.md) | Numbered migrations out of database.py |
| [phase3-test-remediation/](phase3-test-remediation/README.md) | Make the suite trustworthy & TDD-aligned |
| [phase4-frontend-split/](phase4-frontend-split/README.md) | Split the giant files; finish the restructure |
| [phase5-debug-complete/](phase5-debug-complete/README.md) | Fake bridge + adapters so it runs offline |
| **money-path** → [../stage3/](../stage3/README.md) | Live-safety fixes (extracted to stage 3 — Simon's demo session) |
| [phase7-handoff/](phase7-handoff/README.md) | HANDOFF, checklist, docs, retire packs |

## Related packs this roadmap drives (do not duplicate — extend/reference)

| Pack | Relationship |
|---|---|
| [../stage1/](../stage1/README.md) | The Aug-8 remediation, mostly done. Phase 4 here folds in its phase-3 frontend tasks. |
| [../stage3/](../stage3/README.md) | The money-path, extracted (Simon-gated). Not part of stage 2's today-work. |
| [../frontend/restructure/](../frontend/restructure/README.md) | The 001 restructure pack (stalled 0/13). Phase 4 here drives it — starting with its unanswered QUESTIONS. |
| [../infra/local-debug-mode/](../infra/local-debug-mode/README.md) | Debug-mode pack. Phase 5 here drives its remaining tasks. 010 (config) + login are already done. |

## Sequencing & priority

Phases 1–3 are **independent and unblocked** — do them in parallel/any order; they are the
highest-value, lowest-risk foundation. Phase 4 (frontend split) is large and gated on Darren
answering the restructure QUESTIONS. Phase 5 makes debug mode fully usable. The money-path
(**[stage 3](../stage3/README.md)**) is gated on **Simon** (sign-off + demo) and is not part of
stage 2. Phase 7 closes out. Recommended first move: **phase 1 (usability)** — it is the owner's
stated top pain and is pure view-layer, no money.

## Decisions locked with the user (2026-08-11)

| Decision | Choice | Source |
|---|---|---|
| Make a handoff roadmap now | Yes — this pack, plus HANDOFF.md + questions-routing | user |
| Questions an agent can't answer | Go to docs/questions/ for Simon | user |
| Structure | Phased, one workstream per phase; reference existing packs, don't fork | user + /spec rule |

## Open questions

Full write-ups in [QUESTIONS.md](QUESTIONS.md); short list:

- Onboarding scope — is the first-run checklist the right centerpiece? (Darren)
- The 4 unanswered frontend-restructure QUESTIONS block phase 4 (Darren)
- The debug-mode QUESTIONS (fake-stream format, fill modeling, first-run password) (Darren/Simon)
- Money-path defaults already provisionally answered in stage1 QUESTIONS (Simon confirms)

## Out of scope

- New trading strategies / signal logic — this roadmap is usability, safety and maintainability only.
- Multi-user auth, cloud/remote hardening, cluster work — single-node localhost (see stage1).
- Anything that changes how the system trades except the Simon-signed phase-6 tasks.
