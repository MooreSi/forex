# Handoff-readiness review — 2026-08-11 (end of the stage-2 sweep)

Point-in-time review after the stage-2 sweep landed (commits `9ff9fba` → `2d17b94`). Two parts:
a **circuit-breaker design review** (Darren's notes.md question — fresh analysis, code read in
full), and a **re-measured state of the branch** (every number below re-run today, not quoted
from PROGRESS). Caveat stated up front: the sweep itself was executed by the same agent writing
this review — the numbers are mechanical and reproducible, but an independent pass
(`/code-review ultra` on the branch) is the honest complement before the Simon session.

---

## Part 1 — Circuit-breaker design review

Read in full: `services/risk/circuit_breaker_repo.py`, the gate site
(`services/trading/open_trade.py:191-198`), the recording site
(`services/trading/close_trade.py:242-263`), `services/signals/resolution.py:123`, the header
badge (`frontend/app.py`), and the reset path.

### What is designed well

- **The gate sits at the single choke point.** `open_trade()` — the one function that inserts a
  trade and places the order — raises while the breaker is active. Signal generation continues;
  open positions keep being managed; nothing is auto-closed. That is the right shape for a halt.
- **State survives restarts.** Persisted in `vantage_risk_settings`
  (`active_until`/`consec_losses`), not in memory; `is_active` is recomputed from the clock, so
  a restart mid-cooldown stays halted.
- **Trigger semantics are sensible.** N consecutive *live* losses (demo/sim outcomes don't
  count — `mt5_ticket` guard); a win or breakeven resets the streak; the counter resets on
  trigger so a fresh full streak is needed after a cooldown.
- **Alert-once is handled properly.** `just_triggered` distinguishes "this loss tripped it"
  from "a loss closed during an already-active cooldown" — no re-notification spam.
- **Manual reset exists** (`reset_circuit_breaker`, surfaced in Risk Settings), and the header
  badge polls state every 5s with a countdown.
- **Two-node behaviour is correct by construction:** the counter/active_until live in risk
  settings, and `update_risk_settings` forwards over the sync channel, so a breaker tripped on
  one node halts the pair.
- **Concurrency is safe today:** the read-modify-write of the loss counter runs on the single
  dedicated DB worker thread (`to_db_thread`), and every write invalidates the 10s risk-settings
  memo, so increments cannot be lost through the cache. (Fragile-if: any future caller invoking
  `record_live_trade_outcome` off that worker thread would reopen a lost-update race — worth a
  comment at the definition, nothing more today.)

### The two real gaps (both already stage3/050's scope — now with evidence)

1. **It ships disarmed.** `circuit_breaker_enabled` defaults to 0. Every property above is
   moot until the user finds the toggle. Arming it by default is exactly stage3/050 and needs
   Simon (a behaviour change to when orders are refused).
2. **A failed outcome recording is swallowed at DEBUG level** —
   `close_trade.py:262: except Exception: log.debug("[CB] outcome recording skipped")`. A locked
   DB or transient error during a losing close silently *under-counts the loss streak*, which
   means the breaker can fail to trip precisely during the kind of trouble that produces loss
   streaks. Same pattern two blocks up for the risk-governor halts (`[RG] post-close halt check
   skipped`, also debug). **These lines sit inside the frozen close path**, so even the
   log-level fix is Simon-gated — folded into stage3/050's task file as a named line item.

### Smaller observations (no action without Simon)

- `won = total_pnl >= 0` counts an exact-zero close as a win (streak reset). Defensible; note
  that fees can drag a "breakeven" slightly negative, making it count as a loss — conservative
  direction, fine.
- `threshold <= 0` silently disables triggering while leaving the breaker "enabled" — worth a
  settings-UI validation eventually, not a live risk (default is 3).
- Cooldown expiry is passive (clock comparison) — correct; no background task to crash.

**Verdict:** the mechanism is genuinely well-designed — right choke point, persistent,
node-synced, alert-once, resettable. Its weaknesses are not design flaws but *arming and
observability* gaps, and both are already specced for the Simon session (stage3/050).

---

## Part 2 — State of the branch, re-measured today

| Measure | 2026-08-08 review | 2026-08-11 (today, re-run) |
|---|---|---|
| `tools.checks all` | coverage step could not pass | **all 7 green** at every stage-2 commit (latest: suite 442s) |
| Controller-boundary contract | 59, baselined | **50**, baseline tightened (engine-panel lane done) |
| Silent `except: pass` (frontend) | 31 → 44 (regressing) | **40**, now gated shrink-only with no slack |
| `ui.timer` polls | 33 | 31 (migration to a poll helper still open) |
| Test files with zero tests | 13 | **0**, structurally banned |
| Local `fresh_db` copies | 114 | **66**, shrinking baseline |
| `MetaTrader5` importable from tests | unguarded | **banned by gate** |
| Legacy-DB upgrade proof | none | 3 historical shapes fixture-tested to head |
| Debug mode | boots, nothing ticks | full offline e2e signal→open→manage→close on fakes; only the `_make_bridge` seam (Simon) unwired |
| Files over 800 LOC (frontend) | 8 | 8 — unchanged: settings 3112, app 1605, history 1415, ai_trade_analysis 1250, test_panel 1245, breakout 918, chart 839, reversal 803 |
| NiceGUI-patch canary | none (patch targets 3.12, installed 3.15) | canary green — patches verified to still land |

### What this review says is left, in priority order

1. **Stage 3 / the Simon session** — the only live-money blocker. The pack is session-ready:
   [stage3/SIMON-SESSION.md](../../todo/refactor/stage3/SIMON-SESSION.md) (decisions Part A,
   demos Part B incl. the debug seam), and the questions queue is a one-pass read
   ([docs/questions/README.md](../../questions/README.md)).
2. **Push the branch** — CI exists but has never run; "CI green" on the give-to-simon checklist
   is unfalsifiable until the first push (Q003).
3. **Phase-4 remainder** (maintainability, not safety): restructure lanes 030–060 (50 → 0 minus
   the Simon-gated trading/risk lane), the `settings.py`/`history.py`/`app.py` splits,
   timer→poll migration, the 40 remaining silent excepts.
4. **Independent review**: this document was written by the agent that did the work. Run
   `/code-review ultra` on the branch for a multi-agent pass that owes this session nothing.

### Pre-existing debt surfaced (not new, now recorded)

- 9 links reference `docs/specs/` which does not exist at HEAD (incl. the restructure pack's
  anchor spec `001-frontend-restructure.md`) — decide where specs live.
- The four built-but-unwired modules remain ledgered in the orphan allowlist awaiting Q002.
