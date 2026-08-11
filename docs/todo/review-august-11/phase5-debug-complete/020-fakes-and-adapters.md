# 020 — Fake Telegram + canned news/AI/email (drives local-debug-mode 030/040)

**Status:** not started · **Touches money:** no · **Layer:** service/utils
**Drives:** [../../infra/local-debug-mode/030-fake-telegram.md](../../infra/local-debug-mode/030-fake-telegram.md) + [../../infra/local-debug-mode/040-fake-news-ai-email.md](../../infra/local-debug-mode/040-fake-news-ai-email.md).

## Problem

A debug boot still tries outbound Telegram/news/AI/email; without them the signal path can't be
exercised offline, and any live call is a network dependency in debug.

## What to do (per the driven tasks — each carries its TDD contract)

1. Fake Telegram reader replaying scripted signal messages through the real parser (`is_debug()`
   guard at the reader boundary; outbound alerts/bot no-op in debug).
2. Canned news/AI/email behind `is_debug()` at each lowest fetch boundary (news_calendar,
   test_signal/news_filter, ai/provider complete+vision, ai/claude_ai RSS, email_service, model-refresh
   loop). Canned news = one high-impact event ~2h out so the news path is exercised, not skipped.
3. Tests (per the driven tasks): patch the transport, assert untouched in debug; negative control =
   debug-off calls the transport. `python -m tools.checks all`.

## Acceptance
- A debug boot makes **zero** outbound requests (verify by patching transports); a scripted signal
  reaches the parser and yields a signal row. Behaviour with debug off unchanged. Green suite.
