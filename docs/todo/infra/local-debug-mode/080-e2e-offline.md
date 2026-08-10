# 080 — Offline e2e: signal → open → manage → close

**Status:** not started
**Depends on:** 020, 030, 040, 050 (full offline boot must exist)
**Touches money:** no — everything runs on the fakes; **no test may place, close or modify a
real or demo MT5 order** (golden rule; structurally guaranteed here because debug mode cannot
construct a real bridge)
**Layer:** tools/tests
**Leverage:** the boot smoke in `tools/checks`; `tests/conftest.py` DB isolation fixtures;
scenario files from 020/030

## Problem

Nothing proves the refactored system works end-to-end. Unit and characterization tests pin
pieces; no test boots the composed app and walks a signal through parse → risk → placement →
monitoring → close. That is the exact confidence Darren needs before handing the refactor back.

## Decision

New `tests/e2e/` package, marked (e.g. `@pytest.mark.e2e`) and wired into `tools/checks`:

- A session fixture that boots `backend.src.app.startup()` with `FOREX_DEBUG_MODE=1`, a tmp
  data dir (tmp debug DB, tmp licence store via 050's tool or a pre-generated fixture key), and
  a named scenario; tears down via `shutdown()`.
- Scenario-driven tests asserting against the debug DB and the fake ledger:
  1. scripted signal → parsed signal row appears;
  2. auto-execute → order on the fake bridge, trade row with the fake ticket;
  3. scripted price path crosses TP/SL → monitor manages (BE move / ladder per strategy
     config) and the close is recorded with matching ledger state;
  4. an injected `modify_order` rejection scenario → system behaviour recorded as-is (this
     documents today's behaviour; it must NOT be written to assert the *desired* behaviour that
     SPEC-002/the review fixes will bring — characterization, not aspiration);
  5. offline guarantee: a socket-guard fixture (block outbound connect during e2e) proving
     zero network attempts.

## What must NOT change

- No production code changes in this task. If e2e reveals a bug, it gets its own spec/fix —
  never bend the test (golden rule 2).
- Suite runtime: keep e2e ≤ ~60s (starting value) so `tools.checks all` stays usable; use the
  scenario clock/scripted delays, not real-time sleeps, wherever the loops allow.

## Tests first (TDD)

This task IS the tests. Failure-first still applies: each e2e test is written against the
scenario's expected outcome and must be seen red (e.g. run against a deliberately wrong
scenario expectation) before green. Negative controls:

- `tests/e2e/test_boot_offline.py::test_boot_serves_with_no_network` + control: the socket
  guard itself trips when a connect is attempted (prove the guard can fail).
- `tests/e2e/test_signal_to_close.py::test_signal_becomes_trade_and_closes` — the killer path.
- `tests/e2e/test_error_paths.py::test_injected_modify_rejection_characterized`.

## What to do

1. Read `docs/system/rules/40-testing.md` + `/test` skill; decide the e2e marker + checks
   wiring with the existing `tools/checks` structure.
2. Build the boot fixture (tmp dirs; never the real user data dir or `~/.forex_trader_licence`).
3. Write scenario expectations into the scenario files (single source shared with the fakes).
4. Tests red → green; document runtime in PROGRESS.md.
5. `python -m tools.checks all` (now including e2e).

## Where

- `tests/e2e/` — new; `tools/checks` — register the e2e step

## Acceptance

- `python -m tools.checks all` runs e2e green in CI-like conditions with networking blocked.
- **The killer test:** `test_signal_becomes_trade_and_closes` — the full pipeline, offline.
- Output pasted into PROGRESS.md.

## Notes

Do not run two full suites at once (repo rule — phantom failures). The e2e boot must respect
060's login if it exercises HTTP routes — use the debug-seeded `debug`/`debug` credentials;
backend-level e2e (calling `app`/runtime directly) needs no auth.
