# 030 — Fake Telegram: scripted signals in, alerts no-op out

**Status:** not started
**Depends on:** 010-debug-config.md, 020-fake-mt5-bridge.md
**Touches money:** no (composition-root swap + outbound no-op; no order code edited)
**Layer:** service (telegram/signals) + composition root
**Leverage:** reader buffer contract `reader_listener.py:229`; scanner `runtime.py:863` →
`scan_messages.py:88`; parser `services/signals/parser.py`

## Problem

Signals only enter via a Telethon session (`app.py:171 TelegramReader(config)`) needing Simon's
API id/hash/phone; alerts and bot commands need his bot token (`alerts.py:150`,
`bot_loop.py:50`). Without them the signal → parse → execute path — the heart of the system —
cannot run.

## Decision

- New `backend/src/services/telegram/fake_reader.py` — `FakeTelegramReader` exposing the same
  public surface `TradingRuntime` and `scan_messages` consume (startup/shutdown, the message
  buffer contract), replaying scripted messages (real Telegram signal text shapes, e.g. the
  gold/GD2/instant-entry formats the parser handles) from the scenario files (QUESTIONS.md #2),
  with scheduled delays so the scanner loop picks them up naturally.
- Swap at the composition root: `app.py:171` builds the fake when `is_debug()`.
- Outbound: `alerts.send_message` short-circuits to a log line in debug (one guard at the top,
  `alerts.py:150`); the bot command loop is not started in debug.

## What must NOT change

- `scan_messages`, `parser.py`, and the scanner loop — byte-identical. The fake feeds the
  *existing* pipeline; a fake that bypasses the parser proves nothing.
- `TelegramReader` itself untouched.
- Alerts behaviour with debug off — unchanged, including the existing DB-token lookup.

## Tests first (TDD)

- `tests/core/test_fake_reader.py::test_fake_reader_matches_reader_surface` — the attributes/
  methods runtime + scan_messages use exist with matching shapes — structural (+ negative
  control: remove one, checker fails)
- `::test_scripted_message_reaches_parser` — a scripted gold-signal message ends up as a parsed
  signal row via the real `scan_messages` — wiring
- `::test_edit_and_ordering_semantics` — messages surface in scripted order with scripted
  delays — behaviour
- `tests/core/test_alerts_debug_noop.py::test_send_message_noops_in_debug` — no HTTP attempted
  (assert at the transport boundary), returns success shape — wiring; negative control: debug
  off + fake transport → the HTTP path IS invoked
- `tests/core/test_app_wiring_debug.py::test_reader_swap_in_debug` — composition root picks the
  fake — wiring

## What to do

1. Write the tests; watch them fail.
2. Determine the exact reader surface consumed (grep `_tg_reader`/reader usages in
   `runtime.py`, `scan_messages.py`, frontend) and freeze it in the structural test.
3. Implement `fake_reader.py`; add example signal messages to the scenario files (copy real
   message formats from `parser.py`'s docstrings/tests, NOT from any live data).
4. Composition-root swap + alerts guard + bot-loop skip.
5. `python -m tools.checks all`.

## Where

- `backend/src/services/telegram/fake_reader.py` — new
- `backend/src/app.py:171,207` — swap
- `backend/src/services/telegram/alerts.py:150` — debug guard
- `backend/src/runtime.py:47-49` area / wherever the bot loop task starts — skip in debug

## Acceptance

- In a debug boot, a scripted signal appears in the Parsing tab and (with auto-execute per
  QUESTIONS.md #6) becomes a fake-bridge order.
- **The killer test:** `test_scripted_message_reaches_parser`.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

Services must not import `nicegui` and controllers/services layering holds — the fake lives in
`services/telegram`, selection happens in `app.py` (composition root), keeping the import
contracts at zero.
