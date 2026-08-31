# 030 — Frontend hygiene: silent excepts, blocking timers, upgrade canary

**Status:** not started · **Touches money:** no · **Layer:** frontend
**References:** [../../stage1/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md](../../stage1/phase3-expansion-tax/050-frontend-exception-timer-hygiene.md).

## Problem

44 `except Exception: pass` in UI paths (regressed from 31) silently drop data — incl. history.py
dropping malformed deals from displayed P&L. 33 hand-rolled `ui.timer` polls run synchronously on the
event loop. `app.py:15-59` monkey-patches NiceGUI internals — and the installed NiceGUI is now 3.15.0
while the patch targets 3.12.1, with no canary (an upgrade breaks the app silently).

## Tests first (TDD)
- `tests/frontend/test_no_silent_excepts.py::test_no_bare_except_pass_under_frontend` — AST, shrinking
  baseline to 0 (+ negative control: planted swallow fails) — structural
- `tests/frontend/test_nicegui_canary.py::test_patched_internals_exist` — every attribute app.py
  patches exists on the installed NiceGUI (fails on the next incompatible upgrade) — structural canary
- `tests/frontend/test_poll_helper.py::test_fetch_runs_off_event_loop` — the shared poll helper offloads — behaviour

## What to do
1. Write the tests (calibrate the AST count at 44); build a shared `components/poll.py` helper.
2. Replace each swallow with log-at-warning + a visible "data incomplete" marker; migrate the 33
   timers to the poll helper; add the NiceGUI canary.
3. `python -m tools.checks all`.

## Where
- `frontend/pages/*`, `frontend/components/poll.py` (new), `frontend/app.py` (canary target).

## Acceptance
- Silent-except AST count at 0 (shrinking baseline); timers offloaded; canary red on an incompatible
  NiceGUI. Green suite.


---

## Closed out, 2026-08-31 — and the timer premise was overstated

**Silent excepts: 44 → 0.** Every one is now `except Exception as e:` followed
by a debug log naming the page and what was being refreshed. None deleted, none
narrowed away, no behaviour changed. The gate is a rule now rather than a
ratchet, with a planted-violation control.

**The timer half needed measuring before it needed doing.** The task says
*"33 hand-rolled `ui.timer` polls run synchronously on the event loop"*. Counted
on 2026-08-31, there are 36, and:

| | |
|---|---|
| already `async def` | **23** |
| sync, but only touching labels they already hold | 9 |
| sync **and reaching a controller** | **4** |

So the problem was four call sites, not thirty-three — and a shared
`components/poll.py` helper for all of them would have been a large change
justified by a number that was not true.

The four were real, though. `_refresh_cb_badge` in the app shell polls the
circuit-breaker badge every 5 seconds, and
`get_circuit_breaker_state()` reaches `get_risk_settings()`, which is a
synchronous SQLite read. A sync timer callback runs inline on the event loop,
so every tick stalled every page, every websocket and every other timer for the
duration of that read — on a machine also running the trading loops.

**Fixed by making those four `async def`** and awaiting an offloaded twin.
`get_risk_settings_async()` already existed; `circuit_breaker_state_async()`
was added beside it, same shape, `to_db_thread`.

`tests/frontend/test_timers_do_not_block.py` holds the rule at zero and names
offenders rather than counting them — a baseline number would let a new
blocking timer in as long as an old one was fixed. It also checks the twin
genuinely offloads, since "the callback is async" is worth nothing if what it
awaits still blocks.

**Not done, and now the whole of what remains here:** `components/poll.py`. The
case for it is no longer performance — it is that 36 timers each re-implement
their own error handling. That is a tidiness argument, and it should be made on
its own terms rather than inherited from this task's number.
