# Road to handoff — decisions to confirm

Plain-English choices to settle. Each has a **recommendation** — "go with the recommendations" is a
complete answer. Answer inline (write `ANSWER:` under each); answered items stay, annotated.

Routing: **Simon** answers trading/money/licence items; **Darren** answers dev/usability/structure
items. Anything an implementing agent hits later goes in [../../questions/](../../questions/).

## The decisions (quick list)
1. Is the first-run "Start Here" checklist the right onboarding centerpiece? (Darren)
2. The 4 unanswered frontend-restructure questions — needed to unblock phase 4. (Darren)
3. Debug-mode open questions — fake-stream format, fill modeling, first-run password. (Darren/Simon)
4. Confirm the money-path provisional defaults from stage1. (Simon)
5. What is the bar for "giveable to Simon" — does he run it live himself, or does Darren demo it to him first? (Darren/Simon)

---

## 1. Onboarding centerpiece? (Darren)
The onboarding review proposes a first-run "Start Here" checklist (Licence / MT5 connected / Algo on
/ Risk set / Demo-mode) with live ✅/❌ and "Fix this →" jumps, as the main comprehension fix.

- **Yes, build the checklist first (Recommended)** — highest-impact, reuses status the app already
  computes, pure view-layer.
- **Something else** — describe it under ANSWER.

ANSWER:

## 2. Frontend-restructure questions (Darren)
Phase 4 (splitting the giant files, finishing the restructure) is blocked because
`docs/todo/frontend/restructure/QUESTIONS.md` has 4 unanswered decisions. They are structural/naming,
not trading.

- **Go answer them (Recommended)** — unblocks the largest maintainability phase.
- **Defer phase 4** — do usability + foundations first; come back to the split.

ANSWER:

## 3. Debug-mode open questions (Darren/Simon)
`docs/todo/infra/local-debug-mode/QUESTIONS.md` covers: scripted-scenario format for the fake price
stream, whether fills model slippage, and the first-run dashboard-password flow. Needed to finish
phase 5 (make debug mode actually tick).

- **Go with that pack's recommendations (Recommended)** — sensible defaults; nothing money-live.

ANSWER:

## 4. Money-path defaults (Simon)
stage1 `QUESTIONS.md` holds six provisional answers (order-id transport, reconciliation
mode, halt thresholds, backups, update channel, manual positions). They were adopted provisionally so
work could proceed; **Simon confirms** before the [stage 3](../stage3/README.md) money-path ships.

- **Confirm the provisional set (Recommended)** — they keep trading no more aggressive than today.
- **Change specific ones** — note which under ANSWER.

ANSWER:

## 5. The "giveable" bar (Darren/Simon)
Does giveable mean Simon boots and trades it live himself, or Darren demos it to Simon and Simon
signs off the money-path on a shared demo session?

- **Demo-session handoff (Recommended)** — matches the golden-rule requirement that money-path
  changes get Simon's sign-off + a demo before live use.
- **Full self-serve for Simon** — needs the onboarding + docs to be complete enough to run unaided.

ANSWER:

---

## Quick-confirm checklist
- [ ] 1 — onboarding centerpiece?
- [ ] 2 — answer the restructure questions (or defer phase 4)?
- [ ] 3 — debug-mode recommendations?
- [ ] 4 — confirm money-path defaults (Simon)?
- [ ] 5 — giveable bar?
- [x] Anything that changes order placement/closing/sizing is flagged money-touching in the README and its task.
