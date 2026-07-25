# Phase 0 Audit — PROGRESS

_Last updated: 2026-07-25 — audit tooling landed; Checks 1-3 built, validated and run.
Check 4 (wiring tests), the fixture collapse, and the CI guardrails are not started._

## Overall

Built three AST-based checks for the defect class that let extractions be marked "Done"
without being wired in, validated each against a case with a known answer, and ran them
across all 78 `core_*.py` modules. Nothing under `forex_trader/` was modified.

Headline: **10 orphaned functions, 456 LOC of dead code**, three of them undocumented.
Five of the seven on the order path share a single root cause — a partial
`CloseTradeContext` — which is also the dependency gating the trading phase.

## Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Orphan detector | done | AST + alias resolution. Finds 10 functions / 456 LOC. 16 tests including negative controls and the keyword-argument false positive a grep produces. |
| 2 | Inline-twin comparator | done | Classifies identical / diverged / no twin. 12 tests on the normaliser. Surfaced the shared `CloseTradeContext` root cause. |
| 3 | Divergence detector | done | Retro-audit over git history. 6 tests. Validated by independently recovering the documented `core_run_tp_ladder` truncation (`current_sl = new_sl` + the breakeven alert). |
| 4 | Wiring tests (~50) | not started | The check that makes "Done" mean something. |
| 5 | Test fixture collapse | not started | Prerequisite for phases 6-8, not an optimisation. |
| 6 | CI guardrails | partial | Orphan gate done (`--check` + allowlist). LOC / import-contract / SQL / transaction gates not started. |
| 7 | Correct the false tracker rows | not started | `core-engine-wiring/README.md:65` and the deferral rows. |

## What validation was actually done

Each check was pointed at a case with a known answer before being trusted:

- **Check 1** — negative controls assert that wired extractions (`core_open_trade::open_trade`,
  `core_close_trade::close_trade`, `core_monitor_loop::check_sl`,
  `core_risk_governor::rg_check_halt`) are *not* reported, and that a keyword argument named
  `close_full_after_tps` in nine handler modules is not mistaken for a call.
- **Check 2** — the three new orphans were each confirmed by hand before being written up:
  `engine.py:135` imports four names from `core_profit_sync` and `close_full_after_tps` is not
  among them; `engine.py:73` imports only `pnl` from `core_fees_sizing`; `engine.py:39` imports
  `check_sl` from `core_monitor_loop`, not from `core_tp_trigger_tracking`.
- **Check 3** — reproduced the `core_run_tp_ladder` truncation from history alone, naming both
  lost statements that `core-engine-wiring/PROGRESS.md:509-530` records.

## Corrections to earlier assumptions, recorded

- **"There are exactly 50 commits, one per pack."** False. That was an artefact of a shallow
  clone. Real history is 142 commits. Check 3 returned zero findings against the shallow clone
  and only worked after `git fetch --unshallow` — the same "green means fine" failure this pack
  exists to catch, which is why the test suite now skips loudly on a shallow clone instead of
  passing vacuously.
- **"`core_handle_orb_fixed` lost a trailing `log.info` at extraction."** Not at the boundary
  Check 3 examines. At the add-commit (`5d57f7ee`) the extracted copy already contained that
  line; the gap was introduced by a later edit, before wiring. The test asserting otherwise was
  wrong and was corrected to pin the real behaviour and document the limitation.

## Blockers / open

- No usable regression baseline in this container. `MetaTrader5` is Windows-only and the system
  `cryptography` is broken (`No module named '_cffi_backend'`). After installing `httpx`,
  `nicegui` and `cffi`: 1847 passed / 159 failed, versus a documented historical baseline of
  1624 passing with 4 known failures. That gap was not investigated and is not attributable to
  this pack, which adds only new files. **A real baseline is needed before Phase 1 moves any
  code** — without one there is nothing to regress against.
