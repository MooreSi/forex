# Core Engine Wiring — PROGRESS

_Last updated: 2026-07-21 — Tier 1 fully done; Tier 2 mostly done (7 of 8 modules)._

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

## Blockers / open
None. Cross-file-import sweep (`grep -rn "from forex_trader.core.engine import"`)
repeated before/after every wire-in in this batch -- no other direct
imports of the wired symbols found besides the already-fixed
`_apply_fee`/`_platform_fee_rate` case.
