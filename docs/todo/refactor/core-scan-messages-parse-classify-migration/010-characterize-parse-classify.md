# 010 — Characterize parse/classify block

**Status:** Done (2026-07-20)
**Depends on:** none (reuses `core_ai_signal_fallback`, already extracted
and independently characterized)
**Real-money surface:** none -- parsing/classification and DB recording
only.

## Decision

No separate original method exists for this block, so characterization
drives the whole `_scan_messages` for one scan cycle via a fake
`_tg_reader` and a NEW message (no pre-existing `vantage_tg_signals` row,
so sub-pack A's edit logic never fires). Real message text (reused from
`tests/test_signal_parser.py`'s own GD2/Format-A fixtures) drives the
deterministic-parse paths wherever practical; two branches
(`parse_with_learned_rules`'s short-circuit, and GD2's fully-unparseable-
but-gate-matching "queue unrecognised" path) needed the underlying parser
functions mocked directly, since crafting real text that clears
`is_gd2_message`'s gate while failing all three downstream GD2 parsers
proved impractical -- `parse_gd2_partial`/`parse_gd2_instant_entry` are
lenient enough that almost any text with a number or no SL/TP mention
matches one of them. Patched at `forex_trader.core.engine.<name>` (the
name imported into `engine.py`'s own namespace), not
`forex_trader.core.signal_parser.<name>` -- confirmed via a self-caught
patch-target mismatch (patching the origin module silently had no effect,
since `engine.py` imports these by name at module load).

A message's `timestamp` field must be recent (within the 4-minute
staleness window) for "successfully parsed" scenarios to actually reach
`new_signals` -- otherwise the (out-of-scope, sub-pack C's own) staleness
guard intercepts it first and records it as historical instead. Every
"drop"/"queue"/"partial" branch `continue`s before reaching the staleness
guard, so timestamp doesn't matter for those.

Every branch pre-traced via throwaway scripts first.

## Tests first (TDD)

- `tests/core/test_scan_messages_parse_classify_characterization.py`:
  - `parse_with_learned_rules` match -> used directly, skips every
    format-specific gate below it.
  - `format_ab`: no prefix/structural match, AI fallback fails -> dropped;
    AI fallback succeeds -> used directly (currency check skipped, since
    it only runs when the text matched the format_ab gate in the first
    place).
  - `format_ab`: prefix matches, non-XAUUSD currency -> recorded as
    `unsupported_currency`, alerted; a second message from the same
    channel/direction/currency within 15 minutes does NOT re-alert
    (`Direction BUY/SELL`-labeled text only -- the dedup key extraction
    regex doesn't match Format-A's "Buy Gold X-Y" style, a pre-existing,
    narrow gap preserved as-is).
  - `format_ab`: prefix matches, XAUUSD, parses cleanly -> reaches
    `new_signals`.
  - `format_ab`: prefix matches, parse fails, AI fallback fails ->
    `_queue_unrecognised` called.
  - `gd2`: gate doesn't match, AI fallback fails -> dropped; AI fallback
    succeeds -> used directly (deterministic re-parse skipped).
  - `gd2`: gate matches, full parse succeeds -> reaches `new_signals`.
  - `gd2`: gate matches, full parse fails, partial parse succeeds ->
    recorded `pending_followup`, dropped from this cycle.
  - `gd2`: gate matches, full+partial fail, bare instant-entry trigger
    detected -> silently skipped, NOT queued as unrecognised.
  - `gd2`: gate matches, every parser fails (mocked), AI fallback fails ->
    `_queue_unrecognised` called; AI fallback succeeds -> used directly.
  - `auto`: `format_ab` prefix configured and matches -> tried first.
  - `auto`: `format_ab` doesn't match, `gd2` matches, full parse succeeds.
  - `auto`: `gd2` matches, partial parse succeeds -> `pending_followup`,
    dropped.
  - `auto`: neither matches, AI fallback fails -> silently dropped (NOT
    queued as unrecognised -- different from the configured-format
    branches, since an auto-format channel producing noise isn't the same
    signal as a configured format failing).
  - `auto`: neither matches, AI fallback succeeds -> used directly.

## What to do

1. Write the test file using a fake `_tg_reader`, faked
   `_try_ai_signal_fallback`/`_queue_unrecognised`, calling
   `_scan_messages` via `SimulationEngine.__new__(SimulationEngine)`.
2. Confirm the suite passes against current, unmodified `engine.py`.

## Acceptance

- Suite passes against current, unmodified `engine.py`.
- No real or demo MT5 order placed, closed, or modified -- this block
  never calls an order-placing collaborator.
- Reuses the `_reset_thread_local_connection()` / db-worker-thread reset
  helpers from prior packs.

## Notes

18 tests written in `tests/core/test_scan_messages_parse_classify_characterization.py`,
all green on the first run against unmodified `engine.py` after two
self-caught issues: a stale hardcoded message timestamp (fixed by using a
fresh ISO timestamp), and mocking `signal_parser.parse_with_learned_rules`
at the wrong import location (fixed to patch `engine.parse_with_learned_rules`).
No `engine.py` bugs found.
