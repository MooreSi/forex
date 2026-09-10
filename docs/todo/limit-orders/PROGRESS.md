# Limit orders — the keyword decides, not the template — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).

_Last updated: 2026-09-10 — pack scaffolded, no code started, no task signed off._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Routing + template management (010-030): not started
- Revalidation + alerts (040-050): not started
- **Gates:** real-money tasks signed off by the owner? **no** · tests-first honoured? no
- **EA recompile + redeploy to MT5 outstanding** (030) — the owner's action, not a session's
- **Nothing here has been demoed.** Every task changes what a live order does.

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [limit keywords beat the template](010-limit-keywords-beat-the-template.md) | not started | — | the 2026-09-10 fill at 4428.76 is its killer test |
| 020 | [the template manages the fill](020-the-template-manages-the-fill.md) | not started | — | SL measured from the resting price, not the tick |
| 030 | [carry the template on a resting order](030-carry-the-template-on-a-resting-order.md) | not started | — | needs an EA recompile; ship with 020 |
| 040 | [revalidate before the fill](040-revalidate-before-the-fill.md) | not started | — | withdraw and re-arm on the original clock |
| 050 | [announce a discarded limit order](050-announce-a-discarded-limit-order.md) | not started | — | depends on 040 |

## Decisions log
- Keyword decides the entry mechanic, template decides the management (owner, 2026-09-10)
- Grid templates unchanged — already resting (this pack, 2026-09-10)
- Re-check breadth: full parity with the queued path (interview, 2026-09-10)
- Proximity trigger: 10 points from the resting price (interview, 2026-09-10)
- A failed re-check withdraws and re-arms until the original TTL; it does not cancel permanently
  (owner, 2026-09-10 — reversed the same day from the permanent-cancel default)

## Blockers / open
- No task is signed off yet. 010-040 all touch order placement.
- The EA redeploy for 030 needs the owner.
- Two open questions in [QUESTIONS.md](QUESTIONS.md): the SL price reference, and the toggle the
  widened sweep hangs off.
