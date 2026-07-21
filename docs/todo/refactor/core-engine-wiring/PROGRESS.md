# Core Engine Wiring — PROGRESS

_Last updated: 2026-07-21 — Tier 1 and Tier 2 fully done. Tier 3: `core_bot_commands_infra.py`/`core_bridge_watchdog.py`/`core_update_signal.py`/`core_risk_governor.py`/`core_tp_safety_net.py`/`core_untracked_positions.py`/`core_ai_signal_fallback.py` done, `core_bot_commands_trading.py`/`core_profit_sync.py` partial (9 of 16 rows touched). `core_pending_signal_activation.py`, `core_signal_resolution.py` (no standalone `self.` method -- inline half of the still-unwired `open_trade_from_signal`), and everything else touching `open_trade_from_signal`/`open_manual_market_order`/`close_trade` deferred until Tier 5 is wired (see earlier Notes)._

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

| 2026-07-21 | `_cmd_help`/`_cmd_balance`/`_cmd_daily`/`_cmd_status`/`_cmd_trades`/`_cmd_pause`/`_cmd_resume`/`_cmd_risk`/`_cmd_strategy`/`_cmd_dpm_on`/`_cmd_dpm_off`/`_cmd_ime_on`/`_cmd_ime_off` -> `core_bot_commands_readonly.*` (13 fns) | `test_bot_commands_readonly_characterization.py` (25) unchanged-pass + full suite (1620, same 4 pre-existing) | this pack |

## Notes (bot commands readonly wire-in)

Straightforward wire-in, no shared-state ripple -- this pack's own docstring
confirms none of the 13 commands hold any in-memory cache of their own; they
only read account/trade state (via already-wired `get_open_trades`/
`get_sim_account`/`pnl`/`last_closed_tp` collaborators) or flip a
risk-settings/app-config flag. `_cmd_status` takes `self._tg_reader` as an
extra parameter (`cmd_status(args, bridge, tg_reader=None)`); every other
command needed only `self._bridge` or nothing besides `args`. This
completes Tier 2 in full (14 of 14 rows). `_handle_bot_command` (the
dispatcher) still calls `self._cmd_*` unmodified -- untouched by this pack,
per the extraction pack's own note that the dispatcher rewire happens once
all bot-command packs (readonly/infra/trading) are wired.

| 2026-07-21 | `_cmd_restart_bridge`/`_cmd_restart_app`/`_cmd_headless`/`_cmd_switch_live`/`_cmd_switch_demo`/`_cmd_switch_env` -> `core_bot_commands_infra.*`; module-level `_delayed_app_shutdown` removed from engine.py (only referenced internally by the extracted `cmd_restart_app`, no cross-file usage) | `test_bot_commands_infra_characterization.py` (15) unchanged-pass + full suite (1620, same 4 pre-existing) | this pack |

## Notes (bot commands infra wire-in)

First Tier 3 wire-in. Despite touching real process-management (subprocess
spawn, force `os._exit`, live/demo credential switch), no test patch
needed to move: every mock in this pack's test file targets a module
attribute (`subprocess.Popen`, `forex_trader.core.platform_utils.open_restart_log`/
`delayed_relaunch_cmd`, `db.init`/`sync_bridge_credentials_file`,
`cfg_mod.save_to_yaml`) rather than an `engine.<name>` or `SimulationEngine.<name>`
symbol, and all of those modules are imported the same way (by module,
then `.attr` at call time) in both the original engine.py code and the
extracted `core_bot_commands_infra.py` -- so patching the shared module
object affects the call site regardless of which file makes it. The two
exceptions (`SimulationEngine._start_bridge_process` for `_cmd_restart_bridge`,
`SimulationEngine._cmd_restart_app` for `_cmd_headless`) are both passed
into the extracted functions as **injected callables** resolved fresh via
`self.<name>` inside engine.py's thin wrapper on every call, so patching
the class attribute still takes effect exactly as before. `_delayed_app_shutdown`
(a module-level helper, not a method) was removed from engine.py entirely
rather than re-exported, since nothing outside `core_bot_commands_infra.py`
referenced it (confirmed via a repo-wide grep) -- unlike `_apply_fee`/
`_platform_fee_rate`, which stayed re-exported for `ui/pages/history.py`.

| 2026-07-21 | `_cmd_activate` -> `core_bot_commands_trading.cmd_activate`; `_cmd_report` -> `core_bot_commands_trading.cmd_report`. `_cmd_close`/`_cmd_market_price_buy`/`_cmd_market_price_sell` deliberately NOT wired this pass (see Notes) | `test_bot_commands_trading_characterization.py` (28, after mock-target fixes to the 8 activate/report tests) + `test_bot_commands_trading_surface.py` (already passing, unchanged) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (bot commands trading wire-in — PARTIAL, important)

This pack's own module (`core_bot_commands_trading.py`) calls THREE
already-extracted Tier-5 functions directly: `close_trade` (pack 10,
`core_close_trade.py`), `open_trade` (pack 11, `core_open_trade.py`), and
`open_manual_market_order` (pack 13, `core_manual_market_order.py`).
`open_trade` is fully self-contained (verified: no injected
collaborators, matches `self.open_trade`'s current body exactly) so
`_cmd_activate` was safe to wire. But `close_trade` and
`open_manual_market_order` are NOT drop-in equivalents to
`self.close_trade`/`self.open_manual_market_order` in their CURRENT
(still-unwired) form, because both take collaborator state/callbacks by
injection that `core_bot_commands_trading.cmd_close`/
`cmd_market_price_buy`/`cmd_market_price_sell` construct with bare
defaults:

- `cmd_close` builds a fresh default `CloseTradeContext(bridge,
  starting_balance=...)` -- a BRAND NEW empty `TPCache()`, not
  `self._tp_trigger_cache`; empty `scale_out_last_fail`/
  `tp_safety_net_last_alert` dicts, not the engine's real ones; and
  `on_profit`/`schedule_profit_sync`/`background_close_commentary` all
  default to no-op. `self.close_trade` (still the original 250+ line
  inline implementation, Tier 5, not yet wired) actually fires a profit
  sound, schedules a profit-sync retry loop, and kicks off AI/Telegram
  close commentary on every close.
- `cmd_market_price_buy`/`cmd_market_price_sell` call
  `open_manual_market_order(bridge, direction, starting_balance=...)`
  with no `background_open_commentary` passed -- defaults to no-op.
  `self.open_manual_market_order` (confirmed via grep, line ~1476) fires
  `asyncio.create_task(self._background_open_commentary(...))` on every
  manual order placed.

Wiring `_cmd_close`/`_cmd_market_price_buy`/`_cmd_market_price_sell` to
this pack's functions AS-IS would have been a silent, real behavior
regression -- Telegram bot-placed/closed trades would stop firing profit
sound, close/open AI commentary, and profit-sync scheduling, while the
dashboard's own manual-order buttons (still calling the original
`self.*` methods) kept doing all of that. Caught before committing by
reading `core_close_trade.py`'s own docstring (which explicitly flags
every injected collaborator) and grepping `self.open_manual_market_order`
for `create_task`/`_background`/`telegram_alerts` calls not present in
the extracted version's default-argument path.

**Resolution**: left `_cmd_close`/`_cmd_market_price_buy`/
`_cmd_market_price_sell` on their original inline bodies (still calling
`self.close_trade`/`self.open_manual_market_order`) for now. These three
become safe to wire the moment `core_close_trade.py` and
`core_manual_market_order.py` (both Tier 5) are themselves wired into
`self.close_trade`/`self.open_manual_market_order` -- at that point
`self.close_trade` IS `core_close_trade.close_trade` running with the
engine's real `CloseTradeContext`, and passing that same real context
through (rather than constructing a bare default one inline in
`core_bot_commands_trading.py`) is what needs to happen at that time.
Also added one small parity fix while here: `cmd_report`'s Claude-analysis
exception handler was silently swallowing the error with no log line,
unlike `self._cmd_report`'s original `log.warning(...)` -- added the
missing `log.warning` call to `core_bot_commands_trading.py` (a
previously-completed, already-committed extraction pack) for full parity;
confirmed via `test_bot_commands_trading_surface.py`/`_characterization.py`
that no test asserts on log output either way, so this was a safe,
non-behavior-observable addition.

**Fourth lesson for remaining wire-ins**: before wiring any bot-command
(or other thin wrapper) that calls an ALREADY-EXTRACTED Tier-5
order-placing/closing function directly, read that Tier-5 module's own
docstring for injected-collaborator warnings (CloseTradeContext-style
classes, optional `background_*_commentary` callables) and grep the
CURRENT (still-unwired) `self.<method>` body for `create_task`/
`_background`/notification calls not obviously present in the extracted
function's default-argument path. If the extracted function drops a
side-effect that the current `self.<method>` still performs, defer that
specific wire-in until the Tier-5 collaborator itself is wired first.

| 2026-07-21 | `_bridge_watchdog_loop` body -> `core_bridge_watchdog.bridge_watchdog_check`; 3 local vars (`last_restart_at`/`was_connected`/`consecutive_fails`) merged into one `state` dict; per-cycle sleep duration now returned by the check and slept once by the shell instead of scattered `sleep()+continue` calls | `test_bridge_watchdog_characterization.py` (13) unchanged-pass, exact `sleep_calls` sequences preserved + full suite (1620, same 4 pre-existing) | this pack |

## Notes (bridge watchdog wire-in)

Clean sweep-style wire-in, same shape as max_tp_hit/gd_copy_research/
email_scheduler: the extracted `bridge_watchdog_check` returns a sleep
duration instead of calling `asyncio.sleep()` itself, so every one of the
original's several `await asyncio.sleep(N); continue` call sites collapses
to a single `await asyncio.sleep(sleep_for)` at the bottom of the shell's
while loop. Verified this preserves the exact sleep sequence for every
branch (fast-fail-below-threshold, restart-launched, restart-launch-failed,
inhibited, cooldown-blocks-second-restart) via the existing test's
`sleep_calls == [...]` assertions, all unchanged. No shared-instance-state
ripple -- the three watchdog locals were already loop-local, not `self.*`
attributes, so merging them into `state` only touched this one method.
`_start_bridge_process` (Tier-3-adjacent, still not itself "wired" in the
sense of having its own extraction -- it's a large process/Wine-teardown
method deferred to a separate not-yet-migrated background-loops cluster)
stays exactly as before, passed through as the same injected callable
pattern used by `_cmd_restart_bridge`.

| 2026-07-21 | `_sync_profit`/`_schedule_profit_sync`/`_profit_sweep` -> `core_profit_sync.*`; `_close_full_after_tps` deliberately NOT wired (bare `CloseTradeContext`, same reason as `_cmd_close`) | `test_profit_sync_characterization.py` (13, after mock-target fixes to 4 schedule/sweep tests) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (profit sync wire-in — partial, same pattern as bot-commands-trading)

`sync_profit`/`schedule_profit_sync`/`profit_sweep` are fully self-contained
(pure DB read/write + bridge reads, no injected-collaborator dependency) so
all three were safe to wire. `close_full_after_tps` was left on its
original body for the same reason `_cmd_close` was skipped: its rare
residual-position branch builds a bare `CloseTradeContext(bridge)` and
calls `record_close(...)` directly, dropping the engine's real TP cache/
scale-out/TP-safety-net state and close-commentary callback -- unsafe
until `core_close_trade.py` (Tier 5) is wired into `self.close_trade`
first.

Confirmed the third lesson (collaborator patch-target relocation) applied
here too: `_schedule_profit_sync`/`_profit_sweep`'s own tests patched
`SimulationEngine._sync_profit` directly, but once wired,
`schedule_profit_sync`/`profit_sweep` (the extracted functions) call the
module-level `sync_profit` imported into `core_profit_sync`'s own
namespace, bypassing `self._sync_profit` entirely -- even though
`_sync_profit` itself is ALSO now wired (to the very same underlying
function), patching the class method has no effect on a caller that
never goes through `self.*`. Fixed by re-pointing 4 tests' mocks to
`mock.patch.object(core_profit_sync, "sync_profit", ...)`, matching each
fake's new 3-arg signature (`trade_id, ticket, bridge`). No fixture
attribute renaming needed this pack.

| 2026-07-21 | `update_signal` -> `core_update_signal.update_signal` | `test_update_signal_characterization.py` (14) unchanged-pass + full suite (1620, same 4 pre-existing) | this pack |

## Notes (update_signal wire-in + Tier-3 collaborator survey)

Clean wire-in, no ripple -- `update_signal` only touches `bridge.modify_order`
and the `ea_bridge` module singleton directly, both already accessed the
same way (module-level, not via `self.*`) in the original.

Before picking this one, surveyed the REMAINING Tier 3 rows for the same
bare-collaborator-context risk found in `_cmd_close`/`_close_full_after_tps`
by grepping each `core_*.py` module for `CloseTradeContext`/
`background_open_commentary`/`background_close_commentary`/
`open_trade(`/`open_manual_market_order(`/`close_trade(`/`record_close(`/
`open_trade_from_signal(`:

- **Blocked** (calls a collaborator-bearing Tier-5 function with a bare/
  default context, same regression class as `_cmd_close`):
  `core_pending_signal_activation.py` (calls `open_trade_from_signal` with
  no `background_open_commentary`), `core_mt5_position_sync.py` (calls
  `record_close` with a bare `CloseTradeContext`, confirmed earlier),
  `core_orb_report.py`'s `orb_auto_execute` (calls `open_manual_market_order`
  the same way, per its own comments).
- **Safe** (no such call, or calls a genuinely self-contained Tier-5
  function like `open_trade`/`partial_close_trade` that has no injected-
  collaborator dependency): `core_tp_safety_net.py`, `core_untracked_positions.py`,
  `core_ai_signal_fallback.py`, `core_instant_entry.py` (calls `open_trade`
  directly, same as `_cmd_activate`), `core_instant_followup.py`,
  `core_signal_resolution.py`, `core_update_signal.py` (this pack),
  `core_risk_governor.py`, `core_run_tp_ladder.py` (calls
  `partial_close_trade`, which is pure DB bookkeeping with no bridge call
  at all).

This survey narrows the remaining safe-to-wire-now Tier 3 set to:
`core_tp_safety_net.py`, `core_untracked_positions.py`,
`core_ai_signal_fallback.py`, `core_instant_entry.py`,
`core_instant_followup.py`, `core_signal_resolution.py`,
`core_risk_governor.py`, `core_run_tp_ladder.py`. Everything else in
Tier 3 (and likely a good chunk of Tier 4) stays blocked until
`core_close_trade.py`/`core_open_trade_from_signal.py`/
`core_manual_market_order.py` (Tier 5) are wired into
`self.close_trade`/`self.open_trade_from_signal`/
`self.open_manual_market_order` first.

| 2026-07-21 | `is_trading_paused`/`_check_pre_trade_filters`/`_rg_day_start_ts`/`_rg_size_and_check`/`_rg_check_halt`/`_rg_apply_halts_on_close` -> `core_risk_governor.*`; unused `_RR_BYPASS_SOURCES`/`_RG_MIN_TP1_RR`/`_RG_MAX_STOP_ATR` class constants removed | `test_risk_governor_characterization.py` (26, 1 test updated -- see Notes) + `test_risk_governor_surface.py` (26, unchanged) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (risk governor wire-in)

All six methods are pure DB-read/computation, no bridge calls, no
injected-collaborator dependency -- fully self-contained and safe
regardless of which callers (`open_trade`, `_try_activate_pending_signals`,
etc.) are or aren't themselves wired yet, since they don't touch order
placement/closing at all. Added the same kind of missing-log-line parity
fix as `core_bot_commands_trading.py`'s `cmd_report`: `rg_apply_halts_on_close`
was missing the trailing `log.warning("[RG] Trading paused until %.0f: %s", ...)`
call engine.py's original had; added it to `core_risk_governor.py` (plus
the `logging`/`log = logging.getLogger(__name__)` boilerplate it didn't
have yet). No test asserts on it either way.

**One test required a genuine behavioral update, not just a fixture/mock-
target change** -- the first time this has happened in the whole wiring
phase. `core_risk_governor.py`'s own docstring documents a real,
deliberate bug fix made during its 020 extraction: the original
`_rg_apply_halts_on_close` made two SEPARATE top-level `set_app_config()`
calls (`trade_pause_until`, then `risk_halt_reason`), so a crash between
them could leave a pause flag set with no reason. The extraction wrapped
both calls in one outer `with db_module.db():`, making them atomic (the
re-entrant `db()` transaction only commits/rolls back at depth 1, so a
failure on the second nested call rolls back the first too). The 010
characterization suite had a test, `test_rg_apply_halts_on_close_is_not_atomic_today`,
that deliberately forced a mid-write failure and asserted the OLD buggy
outcome (`trade_pause_until` survives, `risk_halt_reason` doesn't) --
written with the explicit expectation (stated in its own docstring) that
it would need updating once this pack got wired. Renamed to
`test_rg_apply_halts_on_close_is_atomic_since_020_fix` and flipped both
assertions to `is None` (neither write survives now). This is NOT a
violation of the "existing characterization test must still pass
unmodified" rule -- that rule protects against *unintended* behavior
drift from the wiring mechanics themselves; this is a *previously
reviewed and accepted* bug fix (already committed, already documented)
finally taking effect for the first time now that the method is wired,
exactly as the original test's own docstring anticipated.

| 2026-07-21 | `_tp_safety_net_sweep`/`_tp_safety_net_check_trade`/`_compute_be_cost_pts` -> `core_tp_safety_net.*`; unused `_TP_SAFETY_NET_ALERT_COOLDOWN` class constant removed | `test_tp_safety_net_characterization.py` (15, after mock-target fixes to 2 tests) + `test_tp_safety_net_surface.py` (unchanged) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (tp_safety_net wire-in)

Only touches `bridge.modify_order`/`get_candles_range`/`get_tick`, DB
writes, and the `ea_bridge` singleton -- no injected-collaborator context
issue like `close_trade`/`open_manual_market_order`. `_tp_safety_net_last_alert`
stays a plain `self.*` dict passed by reference into the extracted
functions (mutated in place), same as before -- no rename needed since
another call site (`_record_close`'s cleanup) already reads/writes it via
the same attribute name and isn't touched by this pack.

Third lesson applied twice more: `test_tp_safety_net_characterization.py`
had `mock.patch.object(SimulationEngine, "_compute_be_cost_pts", ...)` (now
calls `core_tp_safety_net.compute_be_cost_pts` directly) and
`mock.patch.object(SimulationEngine, "get_open_trades"/"_tp_safety_net_check_trade",
...)` in the sweep-continues-past-exception test (now calls
`core_tp_safety_net.get_open_trades`/`tp_safety_net_check_trade` directly,
bypassing `self.*` entirely) -- both re-pointed to the module, with the
fake's signature adjusted to the extracted function's real 4-arg shape
(`trade, now, bridge, last_alert`).

| 2026-07-21 | `get_untracked_mt5_positions` -> `core_untracked_positions.get_untracked_mt5_positions` | `test_untracked_positions_characterization.py` (10) + `test_untracked_positions_surface.py` (unchanged) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (untracked positions wire-in)

Trivial, no-op-risk wire-in -- pure read-only reconciliation (compares
live MT5 tickets against tracked ones, returns the diff), no DB writes, no
order calls, no injected collaborator. This pack's test file never
patched a `SimulationEngine.*`/`self.*` collaborator to begin with (uses
a real fake bridge + real DB-backed `get_open_trades`), so no mock-target
relocation was needed either.

| 2026-07-21 | `_try_ai_signal_fallback`/`_push_ai_recovered_created`/`_apply_sl_adjustment`/`_queue_unrecognised`/`_analyse_unrecognised_message` -> `core_ai_signal_fallback.*` | `test_ai_signal_fallback_characterization.py` (34, after 1 mock-target fix) + `test_ai_signal_fallback_surface.py` (unchanged) + full suite (1620, same 4 pre-existing) | this pack |

## Notes (AI signal fallback wire-in)

No order placement/closing calls anywhere in this module (confirmed via
grep before starting) -- `_apply_sl_adjustment` only touches
`bridge.modify_order`, same self-contained shape as `core_update_signal.py`.
`_is_active_trader_node()` is resolved by the wrapper itself and passed in
as a bool (same pattern as `core_email_scheduler.py`), so the test's
`mock.patch.object(SimulationEngine, "_is_active_trader_node", ...)` stayed
effective unchanged. One relocation needed: `_queue_unrecognised`'s test
patched `SimulationEngine._analyse_unrecognised_message` to verify a task
gets scheduled, but the wired `queue_unrecognised` now calls the extracted
module's own `analyse_unrecognised_message` directly -- re-pointed to
`mock.patch.object(core_ai_signal_fallback, "analyse_unrecognised_message", ...)`.

Also noted (not itself wired this pack): `core_signal_resolution.py` has
no corresponding standalone `self.` method in engine.py to redirect --
its `resolve_open_trade_params` is the FRONT HALF of the still-fully-
inline `open_trade_from_signal` (Tier 5), not a separate method call site.
Wiring it would mean surgically splitting `open_trade_from_signal`'s body
mid-method, which is Tier-5-grade risk, not a standalone Tier-3 item --
removed it from the "safe to wire now" list from the earlier survey.

## Blockers / open
None. Cross-file-import sweep (`grep -rn "from forex_trader.core.engine import"`)
and cross-file attribute-access sweep (`grep -rn "\._attr_name\b"`)
repeated before/after every wire-in in this phase.
