# Test Signal (Bounce) Migration

**Status:** see PROGRESS.md — this header was stale and is not authoritative
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Same pattern as [backend-foundation](../backend-foundation/) and
[breakout-signal-migration](../breakout-signal-migration/) — read those first if new to this.
Reuses the shared `DbAdapter` from backend-foundation's task 010.

## What we're building & why

Third engine ("Bounce"/TestSignal) in the `refactor/` series, after `gd_copy_signal` and
`breakout_signal` (both done). `test_signal` is the largest of the three smaller engines
(721-line `database.py`, 1,952-line `engine.py`) and the most complex: on top of signal
generation + TP/SL management + live dispatch + Claude batch tuning (same shape as the other
two), it also has a 3-second velocity/liquidity-sweep monitor (like breakout_signal's, but with
an extra sweep-reversal detector) and a 2-minute watchdog loop that self-heals dead async tasks
— neither of the other two engines has a watchdog.

**No partial-close mechanism** — unlike gd_copy_signal and breakout_signal, TP1 here only moves
SL to break-even (no banked partial), so the double-counting bug class found in breakout_signal
does not apply. The atomicity gap is different and arguably worse: `_close_signal`'s balance
update is 3-4 fully separate, unguarded connections (read balance, write balance, log entry,
update signal row) with no atomicity at all today, not even the two-connection pattern the
other engines had.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-test-signal-current-behavior.md](010-characterize-test-signal-current-behavior.md) | Characterization tests |
| [020-migrate-test-signal-repo-layer.md](020-migrate-test-signal-repo-layer.md) | Data layer on the shared adapter, transactional |
| [030-extract-test-signal-service-layer.md](030-extract-test-signal-service-layer.md) | Split `engine.py` into service + focused files |
| [040-mt5-connectivity-check.md](040-mt5-connectivity-check.md) | Reuses the isolated MT5 terminal |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Same pattern | Reuse `forex_trader/src/db/`, same 4-task shape | precedent |
| Scope | `test_signal` only. UI, MQL5 EA, sync protocol, `core/engine.py` still out of scope | precedent |
| MT5 validation | Connectivity-only, no order round-trip | precedent |
| Old files | `engine.py`/`database.py` stay in place — external call sites not rewired in this pack | precedent |

## Out of scope

Same as the other two packs, plus: the watchdog loop's self-healing behavior is characterized
by inspection/unit test where feasible, not by actually killing and observing task recovery
under load — that's an integration-test-grade concern beyond what this pack's tests attempt.
