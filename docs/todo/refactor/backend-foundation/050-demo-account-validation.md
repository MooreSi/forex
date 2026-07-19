# 050 — Demo-account validation

**Status:** not started
**Depends on:** 040-extract-gd-copy-service-layer.md
**Real-money surface:** yes — needs user sign-off before implementation
**Leverage:** `gd_copy_signal_service.py` (040)

## Problem

010-040 prove the new structure is behavior-equivalent under test, but never against a live
MT5 connection — only against characterization tests with externals mocked. Before this
pattern is trusted for future engines, it needs one real end-to-end run against an actual
(demo) MT5 account.

## Decision

BLOCKED until Simon supplies demo MT5 credentials/config for `forex-refactor2`, kept separate
from the live app's `config.yaml`. Once available, this task connects the new
`gd_copy_signal_service.py` to the demo account (paper/demo order path only) and confirms
signal generation + simulated order handling behave as expected — no live orders, no EA
modification, no UI changes.

## Tests first (TDD)

- `tests/gd_copy_signal/test_demo_integration.py` — an integration test (marked slow/manual,
  not part of the default fast suite) that runs a signal through the real demo MT5 connection
  and asserts it behaves per 020's characterized expectations.

## What to do

1. **STOP** — wait for Simon's explicit sign-off on this task file, plus demo MT5 credentials,
   before writing any implementation code. Only the test skeleton may be drafted ahead of time.
2. Once signed off: wire a demo-only `config.yaml` for `forex-refactor2` (gitignored, never the
   live app's config).
3. Implement `test_demo_integration.py` against the demo account.
4. Run once manually, capture output, report results to Simon — this test depends on an
   external network + broker connection, so it isn't part of routine dev/CI runs.

## Where

- `forex-refactor2/config.yaml` (new, local-only, gitignored, demo credentials)
- `tests/gd_copy_signal/test_demo_integration.py` (new)

## Acceptance

- Explicit sign-off received before any implementation step beyond the test skeleton.
- Demo-only connection confirmed — never touches the live account or the live app's config.
- Signal generation and simulated order handling match 020's characterized expectations.

## Notes

This is the only task in this pack touching anything resembling live trading infrastructure.
Everything else (010-040) is pure code structure, provable entirely through tests without a
market connection.
