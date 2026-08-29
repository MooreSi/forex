# 060 — Protective halts ON by default; breaker recording un-swallowed

**Status:** **partly built 2026-08-29.** The number inconsistency and the swallowed
failures are fixed. The default flips for the two enabled flags are NOT done, and
the live account needs Simon (see 011). Not Done.
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

---

## Built 2026-08-29 (market closed, no demo yet)

Thresholds came from Simon's confirmed answer, not from me: **3% daily loss,
10% drawdown, 3 consecutive losses** (001-trading-defaults, 25 Aug).

### The same limit was written down three times, with three different numbers

Not the problem the spec describes, and a worse one. `max_total_drawdown_pct`
was 8.0 in the schema, 8.0 in the Settings screen, and **20.0** as the fallback
in `governor.py` — the function that actually decides whether trading stops.
`max_daily_loss_pct` was 3.0 in the schema and **20.0** in the same enforcement
path.

A fallback only applies when the key is missing, which is exactly when the
configuration is least trustworthy — and the loosest of the three numbers was
the one in the enforcement path. All three now read 3% and 10%.

Tested behaviourally as well as textually: with the key absent, a 4% daily loss
now halts and a 2% loss does not. A textual check alone would pass against a
fallback of 0, which never halts at all.

### The swallowed failures

Both post-close blocks reported at DEBUG:

```python
except Exception as _rg_e:
    log.debug("[RG] post-close halt check skipped: %s", _rg_e)
except Exception as _cb_e:
    log.debug("[CB] outcome recording skipped: %s", _cb_e)
```

In a 50 MB log that is invisible. A broken check makes the halts look like they
simply have not fired yet, which is indistinguishable from not having lost
enough. Both now go through `_notify_halt_check_failed`: an ERROR log and a
Telegram message.

**These sit inside `record_close`, which is frozen.** Only the reporting
changed — the close still records and returns the same value — and the new
notification is wrapped so it can never escape. A test plants a failure and
asserts the notifier returns normally with no loop, no telegram and no
database; removing that wrapper fails seven tests.

### Not done

- **The two `enabled` default flips.** They are ALTER-column defaults, so
  flipping them changes nothing for any existing install, including Simon's.
  The useful action there is a settings change on his account, which is
  [011](../../../simon-handover/011-your-halt-settings-do-not-match-what-you-confirmed.md).
- **The thresholds as Expert Tunables.** They are already editable in
  Settings > Risk; a second place to set the same number invites drift, which
  is the bug this task just fixed.
- **The killer demo:** trip the breaker on demo and confirm the next signal is
  refused.

### Found, and it is Simon's to act on

His demo account has the **risk governor OFF** and **max daily loss at 20%**,
not the 3% he confirmed. The governor being off is why the daily-loss limit has
never fired — `close_trade.py` already carried a note saying exactly that.
Written up as 011.
