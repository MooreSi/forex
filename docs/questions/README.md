# Open questions — the deferred-decision queue

**What this is.** A parking lot for decisions that can be settled *after* the
work, not before. The working method right now:

1. **Keep moving.** Work does not stall waiting for an answer.
2. **Decide provisionally.** Where a decision is needed to proceed, a sensible
   default is chosen and the system is built to run on it.
3. **Make sure it runs.** Every provisional decision is one the app works under
   today — green suite, boots, trades on demo safely.
4. **Hand the queue to the decision-maker.** These files are then reviewed in
   one pass (primarily by the owner's brother, who holds the trading/business
   calls) and each answer is confirmed or overridden.

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

## The queue

| # | Question | Who decides | Provisional default | Consumed by |
|---|---|---|---|---|
| [001](001-trading-defaults.md) | The six trading/ops defaults (id transport, reconciliation, halts, backups, update channel, manual positions) | brother | recommendations adopted | review-aug-08 phase 1–2 |
| [002](002-unwired-modules.md) | Four built-but-unwired modules: wire, keep, or remove? | brother (2 of 4) / Darren | leave as recorded debt; keep the backtest tool | review-aug-08 phase3/010 |
| [003](003-version-control-and-ci.md) | Where does version control live, and is there a remote? | Darren | none yet — blocks CI | review-aug-08 phase4/010 |
| [004](004-news-no-data-policy.md) | When news data is missing/stale, trade through or pause opens? | brother | keep current behaviour (trade through), logged loudly | review-aug-08 phase2/060 |
| [005](005-fact-finding.md) | Facts only the operator knows (live-log contents, licence-secret rotation, is the update client live, is retention on) | Darren / brother | assumptions recorded per item | scopes several tasks |
| [006](006-onboarding-strings.md) | Onboarding wording: checklist rows, tab subtitles, empty-state prompts | Darren | review-proposed wording adopted; edit the data files | stage2 phase 1 |

## Status at a glance

_Last updated: 2026-08-11._

- **Answered:** 0 of 6
- Deployment topology (single, localhost-only) was answered 2026-08-08 and is
  already folded into the plan — see the review pack, not this queue.
