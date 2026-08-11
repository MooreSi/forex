# 060 — Protective halts ON by default; breaker recording un-swallowed

**Status:** not started
**Depends on:** none
**Touches money:** YES — run `/safe-change` first (it changes when the system may open trades).
Not Done without owner sign-off + a demo session.
**Layer:** service + config
**Leverage:** the halts already exist (daily-loss, drawdown, circuit breaker) — this flips defaults
and fixes their wiring, it builds nothing new

## Problem

Every protective halt defaults OFF (review risk M1): daily-loss cap, drawdown halt, circuit
breaker. Always-on protection is effectively only `max_open_trades=1` and lot caps. Worse, the
breaker's own recording after a live close sits in `except: log.debug`
(`close_trade.py:242-263`, review data H6) — live losses can silently never trip it — and its
balance input can come from a sim ledger known to drift ($707 vs $1122, review backend H7).

## Decision

Flip the three halts to default ON with conservative thresholds (QUESTIONS.md #3), make breaker
recording failures loud (error log + notification — still non-fatal to the close itself), and make
the breaker read real broker balance, falling back to sim only with an explicit warning. Halts
pause new opens only; they never auto-close existing positions.

## What must NOT change

- The frozen close path — the `except` fix wraps the *breaker recording call site*, not the close
  functions themselves. Zero reshaping.
- Halt semantics: pause-new-opens-only. Nothing in this task closes positions.
- Existing users' explicit config: an installed config that explicitly set a halt OFF stays OFF —
  only the *absent-key default* changes.
- `max_open_trades=1` default.

## Tests first (TDD)

- `tests/risk/test_halt_defaults.py::test_daily_loss_halt_default_on` (+ drawdown, breaker) —
  absent config key → halt active with the locked threshold — surface
- `::test_explicit_off_in_config_is_respected` — negative control for the default flip — control
- `tests/risk/test_breaker_recording.py::test_breaker_record_failure_is_loud` — planted failure in
  recording → error log + notification, close outcome unaffected — regression
- `::test_breaker_uses_broker_balance_when_available` / `::test_sim_fallback_warns` — behaviour
- `tests/risk/test_halt_blocks_opens.py::test_halted_system_opens_nothing` + negative control
  (unhalted system does open via fakes) — behaviour + control

## What to do

1. QUESTIONS.md #3 must be answered first — thresholds are the owner's numbers, not mine.
2. Write the tests above; run them; confirm they fail for the right reason.
3. Flip the three defaults where the config schema defines them; run each threshold through
   `/add-tunable` so they're editable in Expert Tunables.
4. Replace `except: log.debug` at `close_trade.py:242-263` call site with error-log + notify.
5. Point the breaker's balance source at broker truth with warned sim fallback.
6. `python -m tools.checks all`.

## Where

- config schema / defaults (locate via `backend/src/config/`) — the three defaults
- `backend/src/services/risk/` — breaker balance source
- the breaker-recording call site around `close_trade.py:242-263` — caller-side fix only

## Acceptance

- A fresh install (no config) trades with all three halts armed; tripping any halt provably blocks
  the next open.
- **The killer test (demo session):** trip the breaker threshold with demo closes; the next demo
  signal is refused with a clear halt message.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- 2026-08-11 design review confirms both gaps with the mechanism otherwise well-designed (right
  choke point, restart-safe, node-synced, alert-once): see
  [docs/reviews/2026-08-11/handoff-readiness-review.md](../../../reviews/2026-08-11/handoff-readiness-review.md)
  Part 1. Also un-swallow the sibling `[RG] post-close halt check skipped` debug-level except two
  blocks above the breaker call site — same failure class, same fix, same frozen-path constraint.
- Related: the check-then-act race on these same gates is phase2/030 — don't fix it here, but keep
  the gate call sites tidy for it.
- Upgrade note for CHANGELOG (docs phase of this pack is folded into phase 4): existing users who
  never set the halts will see them switch on — that must be in the release notes.
