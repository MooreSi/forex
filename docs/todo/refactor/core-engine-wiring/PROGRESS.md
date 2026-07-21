# Core Engine Wiring — PROGRESS

_Last updated: 2026-07-21 — Tier 1 fully done; Tier 2 8 of 14 rows done._

## Log

| Date | Module wired | Verification | Commit |
|---|---|---|---|
| 2026-07-21 | `_check_sl` -> `core_monitor_loop.check_sl` | `test_monitor_loop_characterization.py` (18) unchanged-pass + full suite (1620, same 4 pre-existing) | this pack |
| 2026-07-21 | `_price_in_entry_range` -> `core_scan_messages_auto_execute.price_in_entry_range` | `test_risk_governor_characterization.py` (26) unchanged-pass + full suite | this pack |
| 2026-07-21 | module-level `_tp_level_from_extreme` -> `core_max_tp_hit._tp_level_from_extreme` (import, old def removed) | `test_max_tp_hit_characterization.py` (14) unchanged-pass + full suite | this pack |
| 2026-07-21 | `pnl` -> `core_fees_sizing.pnl` | `test_fees_sizing_characterization.py`/`test_mt5_history_characterization.py` (21) unchanged-pass + full suite | this pack |
| 2026-07-21 | `compute_mt5_performance` -> `core_mt5_performance.compute_mt5_performance`; module-level `_platform_fee_rate`/`_apply_fee` removed and re-exported via import (still needed by `ui/pages/history.py`, which imports them directly from `engine`) | `test_mt5_history_characterization.py` (21) unchanged-pass + full suite | this pack |

## Notes

**Found and fixed a real cross-file dependency before it could break anything**:
`ui/pages/history.py` imports `_apply_fee`/`_platform_fee_rate` directly from
`forex_trader.core.engine` (`from forex_trader.core.engine import _apply_fee,
_platform_fee_rate`). Deleting these module-level functions outright (as
initially done) would have broken that import at runtime. Fixed by
importing the extracted versions under the same names in `engine.py`
instead of deleting them -- `history.py`'s import keeps working unchanged.
Before continuing further wire-ins, swept the whole codebase for every
`from forex_trader.core.engine import ...` site to confirm no other such
dependency exists (`app_lifecycle.py` imports the `SimulationEngine`
class itself, always safe; `self_healer.py`'s `Engine` import is a
pre-existing, never-executed `TYPE_CHECKING`-only stale reference,
unrelated). This check should be repeated before every future wire-in
that removes rather than delegates a module-level (non-method) symbol.

| 2026-07-21 | `get_total_deposits` -> `core_total_deposits.get_total_deposits` | full suite (1620) | this pack |
| 2026-07-21 | `get_sim_account`/`update_sim_balance`/`reset_simulation` -> `core_sim_account.*` | `test_sim_account_characterization.py` + full suite | this pack |
| 2026-07-21 | `get_open_trades`/`get_all_trades`/`compute_performance` -> `core_trade_reporting.*` | `test_trade_reporting_characterization.py` + full suite | this pack |
| 2026-07-21 | `import_mt5_history` -> `core_mt5_import.import_mt5_history` | `test_mt5_history_characterization.py` + full suite | this pack |
| 2026-07-21 | `get_tg_signals` -> `core_tg_signals.get_tg_signals` | `test_tg_signals_characterization.py` + full suite | this pack |

| 2026-07-21 | `_get_triggered_tps`/`_last_closed_tp`/`_log_tp_wait_diagnostic`/`_check_tp_hits`/`_get_remaining_lots` -> `core_tp_trigger_tracking.*`; `self._tp_cache`+`self._tp_wait_log_ts` merged into `self._tp_trigger_cache` (`TPCache`) | 13 characterization test files (146 tests) + full suite | this pack |

## Notes (TP trigger tracking wire-in)

**Much bigger test-fixture ripple than any prior wire-in in this phase.**
`_check_tp_hits`/`_get_triggered_tps`/`_log_tp_wait_diagnostic` are called
by nearly every strategy handler, and 12 OTHER packs' own characterization
test files (`test_handle_scale_out_characterization.py`,
`test_dpm_handler_characterization.py`,
`test_handle_scalp_runner_characterization.py`,
`test_handle_conservative_characterization.py`,
`test_handle_conservative_trial_characterization.py`,
`test_handle_no_sl_scale_characterization.py`,
`test_run_tp_ladder_characterization.py`,
`test_handle_orb_fixed_characterization.py`,
`test_handle_protected_scale_characterization.py`,
`test_handle_be_runner_characterization.py`,
`test_handle_trail_stop_characterization.py`,
`test_close_trade_characterization.py`) each construct a bare
`SimulationEngine.__new__(SimulationEngine)` and set the OLD
`e._tp_cache = {}` / `e._tp_wait_log_ts = {}` attributes directly as
fixture setup (since `__init__` never runs). Consolidating those two dicts
into one `TPCache` instance broke all 12 fixtures at once (`AttributeError:
no attribute '_tp_trigger_cache'`).

This is expected, legitimate fallout from wiring shared internal state --
not a behavioral regression -- and distinct from the "existing
characterization test must still pass unmodified" rule, which is about
BEHAVIOR staying identical, not internal attribute names/shapes staying
frozen forever (the whole point of wiring is to change those). Fixed by
updating each fixture to `e._tp_trigger_cache = TPCache()` (importing
`TPCache` from `core_tp_trigger_tracking`) and the two files
(`test_handle_trail_stop_characterization.py`,
`test_close_trade_characterization.py`) that also read/write the cache
dict directly in a test body, updated to go through
`.triggered`/`.wait_log_ts`. Every BEHAVIORAL assertion in all 13 files
(the tp_trigger_tracking pack's own suite plus these 12) is unchanged. All
146 tests across the 13 files pass, plus the full suite (1620 passed, same
4 pre-existing failures).

**Lesson for remaining wire-ins**: before merging/renaming any instance
attribute that's shared across multiple methods (as opposed to a
locally-scoped one only one method touches), grep across the ENTIRE
`tests/` directory for that attribute name first, not just
`engine.py` -- the blast radius can span many other packs' fixtures.

## Blockers / open
None. Cross-file-import sweep (`grep -rn "from forex_trader.core.engine import"`)
and cross-file attribute-access sweep (`grep -rn "\._attr_name\b"`)
repeated before/after every wire-in in this phase.
