# 020 — Trading & risk → `trading_controller`

**Status:** not started
**Depends on:** 010 (so the controller pattern is settled before it is applied to the money path)
**Touches money:** **YES.** Run `/safe-change` before touching anything. This task reroutes call sites that validate, size and place orders, and that read the EA bridge. Not Done without owner sign-off **and** a demo session, both recorded in PROGRESS.md. **Ships alone**, on its own commit and its own release.
**Layer:** frontend → controller
**Leverage:** `backend/src/controllers/trading_controller.py` (103 lines) already owns this domain

## Problem

The trading pages reach past `trading_controller` into risk, signal and broker services:

| File | Line | Import | What it does |
|---|---|---|---|
| `frontend/pages/trading/_manual_entry.py` | 13 | `services.signals.parser.validate_signal` | validates a hand-built signal **before it is executed** |
| `frontend/pages/trading/_manual_entry.py` | 353 | `services.notifications.email_service` | (covered by task 040 — leave it) |
| `frontend/pages/trading/_strategy.py` | 13 | `services.risk.strategy_params as _sp` | reads/writes strategy parameters |
| `frontend/pages/trading/_strategy_cards.py` | 6, 18, 19 | `ai.provider`, `channels.strategy_ai`, `broker.ea_templates` | per-channel strategy + EA template selection |
| `frontend/pages/trading/_strategy_cards.py` | 218 | `services.risk.strategy_params as sp` | as above, function-local |
| `frontend/pages/trading/_strategy_cards.py` | 453 | `services.broker.ea_bridge as _ea_mod` | EA bridge liveness |
| `frontend/pages/trading/_schedule.py` | 18 | `services.risk.schedule as sched` | per-window profit targets that gate entries |
| `frontend/pages/trading/_schedule.py` | 46 | `services.dpm.engine.is_weekly_market_closed` | market-closed check |
| `frontend/pages/trading/_ea_templates.py` | 28 | `services.broker.ea_templates as et` | template CRUD |
| `frontend/app.py` | 1246 | `services.broker.ea_bridge as _ea_bridge_mod` | EA badge in the header |
| `frontend/pages/settings.py` | 2425 | `services.broker.ea_bridge as _ea_bridge_mod` | EA bridge toggle |

`_strategy_cards.py:6` (`ai.provider`) belongs to task 030 — coordinate so the file isn't edited
twice in flight, or let whichever task runs second take it.

## Decision

Extend `trading_controller` with named forwarding functions for signal validation, strategy
parameters, schedule and EA templates; add EA bridge status to it as well, since the header badge and
the settings toggle both want the same read. Reroute every call site. **No function body moves and no
signature changes** — this is an import-path change and nothing else.

The alternative — a separate `risk_controller` — was rejected because the pages here already treat
risk settings, strategy params and schedule as one surface, and `engines_controller` set the
precedent of grouping by *the page's* domain rather than the service's directory.

## What must NOT change

This is the section that matters most in this task.

- **`validate_signal`'s behaviour, byte for byte.** It is the gate between a hand-typed signal and a
  real order. Same arguments, same return shape, same exception types, same rejection reasons.
- **Strategy parameters, schedule windows and profit targets** produce identical values. A schedule
  window that closes entries today closes them after this change, at the same moment.
- **EA template contents and the EA bridge liveness check.** The app only hands a trade to the EA when
  it detects a live connected EA; that detection must be unchanged, because the fallback (Python
  manages the trade) is what makes the feature safe.
- **The close path is not touched at all** by this task. If a call site here appears to reach
  `close_trade`, `record_close`, `_make_close_trade_ctx` or `partial_close_trade`, **stop and ask** —
  it is frozen (CLAUDE.md rule 4).
- **No test may place, close or modify a real or demo MT5 order.** Fakes and sentinels only.
- The function-local import at `app.py:1246` stays function-local.
- Existing tests in `tests/core/`, `tests/controllers/`, `tests/services/` pass unmodified except for
  mock-target relocations, each named in its commit.

## Tests first (TDD)

Characterization comes **first here, before any code moves** — that is the whole protocol for a
money-touching relocation.

- `tests/core/test_manual_entry_characterization.py::test_validate_signal_accepts_and_rejects_the_same_inputs`
  — characterization, written against **unmodified** code. A table of signals (valid, bad entry
  range, missing SL, inverted direction, non-XAUUSD) pinning accept/reject and the exact rejection
  reason.
- `tests/core/test_manual_entry_characterization.py::test_the_characterization_table_can_fail`
  — **negative control**. Feed it a deliberately wrong expectation; assert the table detects it.
- `tests/controllers/test_trading_controller_forwards.py::test_each_new_function_forwards_to_one_service`
  — structural. AST-asserts a call/return body, no logic.
- `tests/frontend/test_trading_pages_wiring.py` — wiring, one case per rewired call site: patch the
  controller function, assert the page handler reaches it with the arguments it used to pass
  directly.
- `tests/frontend/test_trading_pages_wiring.py::test_wiring_detects_a_dropped_argument`
  — **negative control**. A dropped or reordered argument is the realistic failure mode of this kind
  of move; prove the test sees one.
- `tests/frontend/test_trading_pages_wiring.py::test_no_test_in_this_file_can_reach_a_broker`
  — guard rail, asserted rather than assumed, in the style of
  `test_bridge_process_relocation.py::test_no_test_in_this_file_can_spawn_a_process`.

## What to do

1. **Run `/safe-change`.** Do not skip to step 2.
2. Write the characterization tests against unmodified code. Run them; they should pass — that is
   what "characterization" means. Then deliberately break one expectation to prove the table can
   fail, and restore it.
3. Write the wiring and structural tests. Run them; confirm they fail for the right reason.
4. Add the forwarding functions to `trading_controller.py`. Extend `__all__`.
5. Rewire call sites **one file per commit**, running the suite between each: `_schedule.py`,
   `_ea_templates.py`, `_strategy.py`, `_strategy_cards.py`, `_manual_entry.py`, then
   `app.py:1246` and `settings.py:2425`.
6. `python -m tools.checks all` after each commit, not just at the end.
7. **Demo session.** With a demo account: build a signal in the Strategy Builder, validate it, check
   a schedule window blocks an out-of-window entry, and confirm the EA badge reports the same state
   as before. Record what you did and what you saw in PROGRESS.md.
8. Get owner sign-off. Only then mark this Done.

## Where

- `backend/src/controllers/trading_controller.py` — gains forwarding functions
- `frontend/pages/trading/_manual_entry.py`, `_strategy.py`, `_strategy_cards.py`, `_schedule.py`, `_ea_templates.py`
- `frontend/app.py:1246`, `frontend/pages/settings.py:2425`

## Acceptance

- Every listed call site imports from `backend.src.controllers` only.
- The characterization table passes unmodified against the rewired code.
- **The killer test:** on a demo account, a manually built signal that the app *rejected* before this
  change is rejected after it, for the identical stated reason — and one it accepted is accepted,
  with identical entry, SL and TP values.
- Demo session recorded in PROGRESS.md; owner sign-off recorded.
- `python -m tools.checks all` green, real output pasted into PROGRESS.md.

## Notes

- `_strategy_cards.py:6` imports `ai.provider`, which belongs to task 030. Whichever task lands
  second picks it up; note in PROGRESS.md which one that was so the file isn't half-migrated.
- If rerouting any call site turns out to need even a small amount of logic in the controller — a
  loop, a merge, a fallback — that is the signal the logic belongs in the service. Move it there and
  say so in the commit. Do not let it settle in the controller; `history_controller` acquiring
  three-source ledger merges is the recorded example of how that ends.
- If a demo session isn't possible when you reach step 7, do steps 1–6, leave this task
  `blocked — awaiting demo session` in PROGRESS.md, and say so plainly. Do not mark it Done on a
  green suite.
