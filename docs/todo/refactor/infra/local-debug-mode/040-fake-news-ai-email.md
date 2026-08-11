# 040 — Canned news calendar, AI provider, email

**Status:** not started
**Depends on:** 010-debug-config.md
**Touches money:** no
**Layer:** utils + service (ai, notifications)
**Leverage:** `provider.py:50 is_configured` already no-ops without a key; news fetchers are
already isolated functions

## Problem

Three live-path outbound calls remain after 020/030: the news calendar
(`utils/news_calendar.py:124-206` + the duplicate `test_signal/news_filter.py:43-45` — both hit
the network from engine cycles), the AI provider (`services/ai/provider.py` → Anthropic/DeepSeek,
plus the Yahoo RSS at `claude_ai.py:134` and the model-refresh loop), and email
(`notifications/email_service.py`). A debug boot must make zero outbound requests.

## Decision

Guard at the lowest fetch boundary in each module, keyed on `config.is_debug()`:

- News: in debug, both fetchers return canned events from the scenario files (default: one
  high-impact event ~2h in the future, so the news-proximity code path is exercised, not just
  skipped).
- AI: in debug, `provider.complete()` (and vision) return canned deterministic responses tagged
  `[debug-canned]`; the model-refresh loop does not start.
- Email: in debug, `email_service` logs and returns success without sending.

## What must NOT change

- With debug off: every path identical, including the existing no-key no-op behaviour of the AI
  provider.
- No change to the news TTL/caching logic itself (the review's C4 cache bug is NOT fixed here —
  out of scope; the canned source sits below it).

## Tests first (TDD)

- `tests/core/test_news_debug.py::test_canned_events_in_debug` — both fetch sites return the
  scenario events, no urllib/socket use (patch the transport and assert untouched) — wiring
- negative control: debug off + patched transport → transport IS called
- `tests/core/test_ai_debug.py::test_complete_returns_canned_in_debug` — deterministic response,
  no SDK client constructed — wiring (+ negative control)
- `tests/core/test_email_debug.py::test_send_noops_in_debug` — success shape, no HTTP/SMTP —
  wiring (+ negative control)
- `tests/core/test_model_refresh_debug.py::test_refresh_loop_not_started_in_debug` — wiring

## What to do

1. Write the tests; watch them fail.
2. Add the debug branches at: `utils/news_calendar.py` (single entry above the three sources),
   `test_signal/news_filter.py:43`, `services/ai/provider.py` (complete/vision/model-list),
   `services/ai/claude_ai.py:134` (RSS), `services/notifications/email_service.py:105,166` (+
   SMTP path), model-refresh startup site.
3. Add canned news/AI fixtures to the scenario files.
4. `python -m tools.checks all`.

## Where

- files listed above; scenario data in `tools/debug_scenarios/`

## Acceptance

- Debug boot with the network disabled: engines complete full cycles (news proximity computed
  from canned events), AI panels render canned text, no unhandled errors in the log.
- **The killer test:** `test_canned_events_in_debug`'s transport-untouched assertion.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

`utils/` must not import upward — `news_calendar.py` already carries a baselined violation
(→ broker); do not add another. `is_debug()` lives in `config`, which `utils` may import
(config is a bottom layer), so the guard is layering-clean.
