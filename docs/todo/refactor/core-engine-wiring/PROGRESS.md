# Core Engine Wiring — PROGRESS

_Last updated: 2026-07-21 — Tier 1 fully done; Tier 2 13 of 14 rows done (only `core_bot_commands_readonly.py` left)._

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

| 2026-07-21 | `create_signal`/`get_signals`/`activate_signal`/`cancel_signal` -> `core_signals.*` | `test_signal_crud_characterization.py` (12) + full suite | this pack |
| 2026-07-21 | `_load_dpm_calibrated`/`_record_dpm_entry`/`_update_dpm_peak`/`_set_dpm_milestone`/`_finalize_dpm_record` -> `core_dpm_bookkeeping.*`; `self._dpm_calibrated`+`self._dpm_cal_loaded_at`+`self._dpm_recorded` merged into `self._dpm_cache` (`DPMCache`) | `test_dpm_bookkeeping_characterization.py` + `test_dpm_handler_characterization.py` (30) + full suite | this pack |

## Notes (DPM bookkeeping wire-in)

Same class of ripple as the TP-trigger-tracking wire-in, scoped smaller
this time since only 2 files touch this state directly: the DPM
bookkeeping pack's own `test_dpm_bookkeeping_characterization.py` (a
`_FakeEngine` stand-in, not a real `SimulationEngine`, but still setting
the three old attributes) and `test_dpm_handler_characterization.py`
(already touched once for the TP-cache merge). Also found one direct
write OUTSIDE the five wired methods: `_run_dpm_calibration` (Tier 4,
not itself wired yet) sets `self._dpm_cal_loaded_at = 0.0` to force a
reload on the next cycle -- updated to `self._dpm_cache.loaded_at = 0.0`
since it touches the same renamed attribute. Grepped the whole codebase
for the three old names afterward; every remaining hit is a function/
method name (`load_dpm_calibrated`, `_load_dpm_calibrated`) or docstring
text, not an attribute access.

| 2026-07-21 | `_max_tp_checker_loop` body -> `core_max_tp_hit.max_tp_checker_sweep`; `_backfill_max_tp_hit_corrected` fully -> `core_max_tp_hit.backfill_max_tp_hit_corrected` | `test_max_tp_hit_characterization.py` (14) + full suite | this pack |
| 2026-07-21 | `_gd_copy_research_loop` body -> `core_gd_copy_research.gd_copy_research_sweep` | `test_gd_copy_research_characterization.py` (7, after a patch-target fix) + full suite | this pack |

## Notes (max_tp_hit / gd_copy_research wire-ins)

Both are sweep-style background loops where the extraction pack already
established the "sleep/while shell stays in engine.py, per-cycle body
delegates" split, so the wire-in itself was mechanical -- no shared
instance-state ripple this time (`_backfill_max_tp_hit_corrected` has no
loop wrapper at all in the original, so its whole body -- including its
own `sleep(120)` -- was replaced by one call).

`test_gd_copy_research_characterization.py` needed one fix:
`_patched_now()` patched `forex_trader.core.engine.datetime` to control
"now" for the 22:00 UK-time gate. After wiring, `engine.py` no longer
calls `datetime.now(...)` itself for this loop at all -- that computation
now happens inside `core_gd_copy_research.gd_copy_research_sweep`, which
imports its own `datetime` from the `datetime` module. Patching
`engine.datetime` silently stopped affecting anything, so the one test
whose expected outcome actually depended on hitting the 22:00 gate started
failing (the others' expected "no call" outcome happened to still hold
either way, for the wrong reason). Fixed by re-pointing the patch at
`forex_trader.core.core_gd_copy_research.datetime` -- the module where the
call now actually happens. All 7 tests pass again, same assertions.

**Second lesson for remaining wire-ins**: whenever a wired method used to
call `datetime.now(...)` (or any other module-level symbol) directly and
now delegates to an extracted function that makes that same call itself,
any test patching `engine.<name>` to control it needs to be re-pointed at
the extracted module instead -- the computation moved, so the patch target
must move with it. Check for `mock.patch("forex_trader.core.engine.<name>"` in
that pack's test file before/after every such wire-in.

| 2026-07-21 | `_email_scheduler_loop` body -> `core_email_scheduler.email_scheduler_sweep` | `test_email_scheduler_characterization.py` (9, after mock-target fixes) + full suite | this pack |

## Notes (email_scheduler wire-in)

Same "datetime patch target must follow the delegated computation" issue
as gd_copy_research, plus a NEW variant of it: several tests patched
`SimulationEngine.build_orb_report`/`_orb_auto_execute`/
`compute_mt5_performance` directly on the class, expecting the loop to
call them as `self.build_orb_report()` etc. -- but
`core_email_scheduler.email_scheduler_sweep` calls the already-extracted
`core_orb_report.build_orb_report`/`orb_auto_execute` and
`core_mt5_performance.compute_mt5_performance` directly (imported by name
into `core_email_scheduler`'s own namespace), bypassing `self.*` entirely
for this call path. Patching the class had no effect once wired. Fixed by
re-pointing every such mock at `core_email_scheduler.<name>` instead, and
adjusting each fake's signature to match the extracted functions' own
shape (`build_orb_report(bridge)` not `build_orb_report(self)`,
`orb_auto_execute(report, bridge, is_active_trader_node)`,
`compute_mt5_performance(bridge, days)`). `_is_active_trader_node` mocks
were NOT affected -- engine.py's wrapper still calls
`self._is_active_trader_node()` itself and passes the resolved boolean
into the sweep, so that one collaborator's mock target didn't move.

**Third lesson for remaining wire-ins**: check every `mock.patch.object(SimulationEngine,
"<name>", ...)` in a pack's test file, not just `mock.patch("forex_trader.core.engine.<name>")`
-- if the wired method now calls an ALREADY-EXTRACTED collaborator directly
(imported into the new module's own namespace) rather than via `self.<name>()`,
those patches need to move to the new module too. Only collaborators the
wrapper itself still resolves before delegating (like
`self._is_active_trader_node()` here) keep their original patch target.

## Blockers / open
None. Cross-file-import sweep (`grep -rn "from forex_trader.core.engine import"`)
and cross-file attribute-access sweep (`grep -rn "\._attr_name\b"`)
repeated before/after every wire-in in this phase.
