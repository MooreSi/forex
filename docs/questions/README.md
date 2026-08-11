# Open questions — the deferred-decision queue

**What this is.** A parking lot for decisions that can be settled *after* the
work, not before. The working method:

1. **Keep moving.** Work does not stall waiting for an answer.
2. **Decide provisionally.** Where a decision is needed to proceed, a sensible
   default is chosen and the system is built to run on it.
3. **Make sure it runs.** Every provisional decision is one the app works under
   today — green suite, boots, trades on demo safely.
4. **Hand the queue to the decision-maker.** These files are then reviewed in
   one pass and each answer is confirmed or overridden.

**A provisional decision is not a silent one.** Every file below records what
was chosen, why, what it touches, and exactly what changes if the answer comes
back different. An answered question is annotated here (and its choice recorded
in the consuming task), never deleted — the history is the point.

**This is not for money-path sign-off.** Confirming a default here is a
*decision*. It is **not** the same as the owner sign-off + demo session that any
order-placement / closing / sizing change still requires before it ships. Those
gates stay exactly where they are.

## How to answer

Open a file, read "The question" and "Options", write your choice under
**Decision:** at the top (replace `PROVISIONAL — …`), and initial + date it.
If you agree with the provisional default, just write "confirm the provisional".
When every file here is answered, the queue is clear.

---

## Simon's pass (the session agenda walks these in order)

**Start here: [docs/todo/refactor/stage3/SIMON-SESSION.md](../todo/refactor/stage3/SIMON-SESSION.md)**
— Part A is exactly this list, in reading order, with the demo session (Part B) after it.

| # | Question | Provisional default | Status |
|---|---|---|---|
| [001](001-trading-defaults.md) | The six trading/ops defaults (id transport, reconciliation, halts, backups, update channel, manual positions) | recommendations adopted 2026-08-10 | awaiting Simon |
| [002](002-unwired-modules.md) | Four built-but-unwired modules: wire, keep, or remove? (licence client + TEST auth are his) | leave as recorded debt | awaiting Simon (2 of 4) |
| [004](004-news-no-data-policy.md) | News data missing/stale: trade through or pause opens? | keep current (trade through, logged loudly) | awaiting Simon |
| [005](005-fact-finding.md) | Facts only the operator knows (live logs, licence-secret rotation, update client, retention) | assumptions recorded per item | awaiting Simon |
| — | Debug-licence policy (self-licensing via the repo's generator, 30-day expiry, `enforce()` untouched — already implemented) | proceed for local dev | awaiting Simon — [local-debug-mode QUESTIONS #1](../todo/refactor/infra/local-debug-mode/QUESTIONS.md) |
| — | The "giveable" bar: demo-session handoff vs full self-serve | demo-session handoff | awaiting Simon/Darren — [stage2 QUESTIONS #5](../todo/refactor/stage2/QUESTIONS.md) |

## Darren's items

| # | Question | Status |
|---|---|---|
| [003](003-version-control-and-ci.md) | Version control & CI | repo/remote/workflow exist; **open: push the branch** (activates CI) + branch protection |
| [006](006-onboarding-strings.md) | Onboarding wording (checklist rows, tab subtitles, empty-state prompts) | provisional strings shipped 2026-08-11; Darren reviews in the running app, edits the data files |
| — | Frontend-restructure structure choices (app.py split depth, chart.py exemption, split-test depth, release cadence) | answered provisionally with each question's own recommendation 2026-08-11 — [restructure QUESTIONS](../todo/refactor/frontend/restructure/QUESTIONS.md); Darren confirms |
| — | Debug-mode working defaults (scenario format, fill realism, first-run password, debug seed state) | answered provisionally per recommendation 2026-08-11 — [local-debug-mode QUESTIONS](../todo/refactor/infra/local-debug-mode/QUESTIONS.md) #2–#6 |

## Status at a glance

_Last updated: 2026-08-11._

- **Numbered queue:** 1 resolved (003, sub-items open) · 5 awaiting review (001, 002, 004, 005, 006)
- **Pack-level QUESTIONS files:** all answered provisionally (stage1, stage2, restructure,
  local-debug-mode) — annotated inline, awaiting confirmation on the passes above.
- Deployment topology (single, localhost-only) was answered 2026-08-08 and is already folded into
  the plan — see the stage1 pack, not this queue.
