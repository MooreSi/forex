# 028 — One close, two Telegram alerts and two circuit-breaker losses

**Status:** fixed 2026-09-04, test-first, all checks green. NOT demoed — the
fix reshapes the frozen close path, see Sign-off needed.
**Found:** live, 2026-09-04, ticket 1940612275, reported by the owner after
receiving the same "Trade Closed" message twice.
**Touches money:** yes — indirectly. The duplicate could not double-pay the
balance (the compare-and-set already prevented that), but it counted one loss
as two consecutive losses toward the circuit breaker, which halts live
execution.
**Severity:** a phantom halt of live trading for the cooldown, and a
consolidated-ledger outcome overwritten to "be" on every affected trade.

## What was seen

```
XAUUSD Trade Closed ✅
🛑 Stop Loss Hit (after TP2)

Direction: SELL  |  Lots: 0.1  |  Held: ?
MT5 Ticket: 1940612275
Entry: $4437.90  →  Exit: $4437.90
Profit: $+33.03
Strategy: Template: 30 TP1 SL50 and Trail
```

Twice, seconds apart. (Entry and exit match because the stop had been trailed
to breakeven after TP2 — that part is correct.)

## Root cause

Two detectors see the same close and both act on it:

1. the EA's stop fires and it pushes `trade_closed` → `_events._on_trade_closed`
   → `record_close` + the `ea_close` alert;
2. the monitor cycle runs `check_sl` on the same row. That call sits at
   `monitor_cycle.py:210`, **above** the `managed_by == 'ea'` skip twenty
   lines below it, so EA Template trades are not excluded from it.
   `reconcile_sl_hit` only defers while the ticket is still fully open at the
   broker — by then it is not — so it calls `record_close` too and sends its
   own alert.

`apply_full_close` is a compare-and-set (`WHERE trade_id=? AND status='open'`,
bug fixed in stage1 phase2/040) so the trade row and the account balance were
already safe. But it returned `None`: `record_close` never read the rowcount
and handed both callers an identical, full-looking result dict, so the loser
believed it had closed the trade.

Reconciliation had been given a narrower version of this fix in 2026-07 by
excluding `managed_by='ea'` rows from its poll
(`broker/repo.py::fetch_python_managed_open_trades`, whose comment names
ticket 1572181515). The SL path was never covered by it, and three more
callers can race in besides.

Everything *after* the compare-and-set ran twice as well, and three of those
blocks record an outcome rather than re-evaluate one:

- `record_live_trade_outcome` — one loss counted as two consecutive losses.
  At the default threshold of 3, two real losses can trip a breaker that
  blocks live execution for the cooldown. It cannot be spotted afterwards
  either: tripping **resets** the counter, so the evidence deletes itself.
- `push_trade_closed` — the consolidated-ledger upsert is keyed on
  `(node_id, trade_id)`, so the second push lands on the same row. Its
  `gross_pnl` is 0, because the winner already zeroed `remaining_lots`, and 0
  grades as `"be"` — **overwriting the real win or loss**. That is the column
  every win rate on the Edge Dashboard is read from.
- `finalize_dpm_record` — rewritten, with a hold time measured to the wrong
  moment.

## What changed

`apply_full_close` returns whether THIS call is the one that closed the trade
— its rowcount is the only thing that knows, and a caller cannot work it out
by re-reading the row, because by then the winner has written `closed` and
both see the same thing. `record_close`'s result carries it as
`already_closed`, and:

- the six close-alert sites (`reconcile_sl_hit`, `check_profit_close_target`,
  `close_trade`, `position_sync`, `ea_bridge._on_trade_closed`, the template
  placeholder repair) stay silent when it is set;
- the three recording blocks above are gated on `close_recorded`.

The Risk Governor, give-back guard and daily-loss ceiling are deliberately
**not** gated: they measure a limit against the live balance and reach the
same verdict twice, and skipping a protective check to tidy up a duplicate
trades a real risk for a cosmetic one. Two tests pin that as a decision
rather than an oversight.

## Verification

- `tests/trading/test_close_alert_not_sent_twice.py` — 23 cases. Red first:
  11 failed (every duplicate-alert assertion), 7 controls passed, which is
  what proves the controls are not vacuous.
- `tests/trading/test_a_lost_close_race_books_nothing_twice.py` — 12 cases.
  Red first: 5 failed, 7 passed. One of the red ones shows the breaker
  actually **tripping** on a single loss with the threshold at 2.
- `python -m tools.checks all` green (11 checks).

## Sign-off needed

1. **Not demoed.** `record_close` is the frozen close path (CLAUDE.md rule 4)
   and its return contract changed. Owner sign-off plus a demo session before
   this is trusted live. Nothing in the change can place, close or modify an
   order — the only behaviour change is which caller stays silent and which
   caller books the outcome — but that is an argument, not a demo.
2. **Existing corrupted ledger rows are not repaired.** Any trade that was
   closed twice before this fix has `outcome = "be"` in `consolidated_trades`
   regardless of what it really did, so historical win rates on the Edge
   Dashboard are understated. Finding and repairing them is a separate
   decision.
3. **`circuit_breaker_consec_losses` may be carrying phantom losses now**, and
   a breaker that tripped on a doubled streak left no trace. Worth a look at
   the current value before the next live session.
