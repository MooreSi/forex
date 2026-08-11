# Local debug mode — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision). This is how
every agent sees where the work is. Keep it honest: a task reported Done that isn't is the exact
failure mode this repo's rules exist to prevent.

_Last updated: 2026-08-11 — fakes/guards/banner/e2e landed via stage2 phase 5; only the 020 seam
(and 090 docs) remain, seam Simon-gated._

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
| 020 | [fake-mt5-bridge](020-fake-mt5-bridge.md) | **YES** | fake done; **seam blocked on Simon** (2026-08-11) | Claude (for Darren) | FakeMT5Bridge + FakeMarket landed with surface/tick/order/settle/injection tests (tests/services/broker/). `runtime._make_bridge` NOT edited — pinned unchanged by test_make_bridge_debug.py until sign-off + demo |
| 030 | [fake-telegram](030-fake-telegram.md) | no | done (2026-08-11) | Claude (for Darren) | FakeTelegramReader → real scan/parser (killer test); app._make_tg_reader swap; alerts+bot-loop debug no-ops |
| 040 | [fake-news-ai-email](040-fake-news-ai-email.md) | no | done (2026-08-11) | Claude (for Darren) | is_debug() guards at every lowest fetch boundary (news×2, AI complete/vision/RSS/model-refresh, email), canned event 2h out; debug-off negative controls |
| 050 | [debug-licence](050-debug-licence.md) | no | done (2026-08-10) | Claude/Darren | `tools/generate_debug_licence.py` writes a GENUINE key (enforce() untouched, no bypass); installed + verified booting. Simon sign-off on the policy still pending (QUESTIONS #1). |
| 060 | [dashboard-login](060-dashboard-login.md) | no | working — verified via Playwright | Claude/Darren | auth service (scrypt) + thin auth_controller + gate middleware + login page + storage_secret. debug/debug seed in debug mode. Browser-verified: /→/login→dashboard, session persists. CLI setter tool + BAR.md polish still TODO. |
| 070 | [debug-banner](070-debug-banner.md) | no | done (2026-08-11) | Claude (for Darren) | components/debug_banner.py behind the shell's is_debug() gate (BAR.md concept was dropped repo-wide; copy is Darren-editable data) |
| 080 | [e2e-offline](080-e2e-offline.md) | no | done (2026-08-11) | Claude (for Darren) | tests/e2e/test_signal_to_close.py: signal→open→TP1 partial+BE→close AND SL-loss path, all offline; drives the runtime facade directly (startup()'s task supervisors not booted — see stage2 PROGRESS note) |
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
