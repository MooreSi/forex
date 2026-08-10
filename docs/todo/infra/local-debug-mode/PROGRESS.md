# Local debug mode — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision). This is how
every agent sees where the work is. Keep it honest: a task reported Done that isn't is the exact
failure mode this repo's rules exist to prevent.

_Last updated: 2026-08-10 — pack scaffolded, no code started._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

A money-touching task is **not** `done` on a green suite alone — it needs owner sign-off and a demo
session, both recorded in Notes.

## Overall
- Pack: not started (QUESTIONS.md awaiting Darren's inline answers)
- **Gates:** `/safe-change` run on money tasks? no (required before 020) ·
  `python -m tools.checks all` green? no
- **Demo session** (task 020 only): not done — required on Simon's machine before live use

## Tasks

| # | Task | Money | Status | Owner | Notes |
|---|---|---|---|---|---|
| 010 | [debug-config](010-debug-config.md) | no | done (2026-08-10) | Claude/Darren | `debug_mode` flag (env FOREX_DEBUG_MODE > yaml), `is_debug()`, DB isolated to forex_trader_debug.db. 7 tests. Full suite confirming. |
| 020 | [fake-mt5-bridge](020-fake-mt5-bridge.md) | **YES** | surface mapped, ready to build | — | 21-method surface documented in task file; `/safe-change` first; fake+tests non-money, only `runtime.py:170` seam is Simon-gated |
| 030 | [fake-telegram](030-fake-telegram.md) | no | not started | — | |
| 040 | [fake-news-ai-email](040-fake-news-ai-email.md) | no | not started | — | |
| 050 | [debug-licence](050-debug-licence.md) | no | not started | — | blocked on QUESTIONS #1 (Simon sign-off) |
| 060 | [dashboard-login](060-dashboard-login.md) | no | not started | — | independent; can start any time |
| 070 | [debug-banner](070-debug-banner.md) | no | not started | — | BAR.md must be edited+agreed by Darren first |
| 080 | [e2e-offline](080-e2e-offline.md) | no | not started | — | needs 020–050 landed |
| 090 | [docs](090-docs.md) | no | not started | — | last |

## Decisions log
- 2026-08-10 — flat pack; real login both modes; full fake scope incl. AI (source: user interview)
- 2026-08-10 — licence: valid generated key, never edit `enforce()` (source: golden rules; Simon
  sign-off still pending)

## Verification log
Paste the real `python -m tools.checks all` output (or its tail) each time a task lands. Green
output claimed without the paste is not evidence.

- (none yet)

## Blockers / open
- QUESTIONS.md unanswered — implementation must not start on 050 (licence) or 070 (banner copy)
  until answered; 010/060 may proceed on the recommended defaults if Darren says "go with
  recommendations".
