# Core Signal Resolution Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-signal-resolution | done | agent, 2026-07-20 | 33 tests, all green against unmodified `engine.py` (called the full `open_trade_from_signal` through a fake bridge, read resolved values off its `place_order` call log). No `engine.py` bugs found; several test-design corrections along the way (real session-toggle field names, RG's stricter ask/bid-based TP1 R:R floor, RG's double lot cap). |
| 020 | extract-signal-resolution | done | agent, 2026-07-20 | Created `core_signal_resolution.py` (358 lines, 1:1 port). Self-caught and fixed a `starting_balance` mis-derivation before it ever reached a test. 33 new surface tests calling the function directly. 396/396 green in tests/core/. `engine.py` untouched. |

## Blockers / open
None. Pack complete. Next: pack 13 — the back half of `open_trade_from_signal` (atomic
signal-claim, the `open_trade` call, and 6 strategy-specific post-fill `bridge.modify_order`
overrides — same risk class as the deferred `update_signal`). Not started.
