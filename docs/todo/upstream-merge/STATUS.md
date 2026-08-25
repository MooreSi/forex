# Upstream merge — where it actually stands

_Updated 2026-08-25 after the test-repair pass. Read this before trusting the branch._

## The number

| | Pre-merge (`a27df81`) | Merge landed | After repair |
|---|---|---|---|
| passed | 2,076 | 2,941 | **3,042** |
| failed | 1 | 100 | **7** |
| errors | 0 | 7 | **0** |
| collected | 2,077 | 3,048 | 3,059 |

Measured with the same command on both trees (`pytest tests/ -q`), the pre-merge
tree checked out in its own worktree.

**All 7 remaining failures are structural ratchets breaching on upstream's
additions, plus one that already failed before the merge.** Not one is a
behaviour failure. `FAILING-TESTS.txt` is the exact list.

## What the 7 are, precisely

| Test | Why |
|---|---|
| `test_pyproject_metadata::test_build_backend_is_importable` | **Pre-existing.** Fails identically on the pre-merge tree; an environment artefact, untouched by this work. |
| `test_structure_gates::test_the_baseline_matches_reality` | The shrink-only LOC ratchet. **9 of 16** baselined files are over: settings.py +371, runtime.py +246, history.py +176, reversal_panel.py +119, app.py +106, chart.py +99, remote/server.py +60, reversal_engine_repo.py +33. |
| `test_facade_audit` | Runtime method count 87 > baseline 79 — upstream's five new loops (`_auto_template_loop`, `_ea_link_watchdog_loop`, `_signal_snapshot_loop`, `_ref_backfill_loop`, `_closed_market_queue_loop`) plus `_revalidate_pending_orders` and the `schedule_profit_sync` facade. |
| `test_fixture_dedup` (3) | Local `fresh_db` 66 → 95 and `_FakeBridge` 56 → 64. **The refactor's own files still hold exactly 66 and 56** — every excess is upstream's 29 new test files bringing their own fixtures. |
| `test_import_contracts::test_no_contract_has_regressed_against_its_baseline` | Two ratchets: frontend-reaches-backend-through-controllers 62 > 50, and no-nicegui-in-the-backend 3 > 2 (`os_utils.restart_app` calls `app.shutdown()`). |

**No baseline was raised.** One was *lowered*: silent `except: pass` under
`frontend/` went 40 → 38.

### Both zero-enforced contracts are clean

`controllers-never-import-the-database`, `controllers-never-import-repos` and
`frontend-never-imports-the-database` are all back at zero. Restoring the last
one meant moving upstream's `_template_group_map` and
`_comment_attribution_maps` out of `frontend/pages/history.py` (a NiceGUI page
running multi-table SQL) into `analytics/trade_history_repo`, with the async
entry points on `analytics/ticket_maps` so the controller imports a service and
never a repo.

## Defects the repair pass found — the reason it was worth doing

Every one of these was live in the merged tree and would have shipped:

| Defect | Consequence |
|---|---|
| `monitor_cycle` had **no `STRATEGY_FIXED_RR` branch** | Such a trade fell through to `handle_scale_out`, which partial-closes against tp1/tp2/tp3 — the bug class upstream's test calls "fabricated $40,730 of PnL". |
| `scan_messages` **stripped `stop_loss` to None** with SL Parsing off | The signal went on with **no stop at all**, instead of the configured fallback distance. |
| The same loop had **no per-message guard** | One malformed message abandoned the whole scan pass, leaving every later message unparsed. |
| **Three upstream modules were never wired** | `core_equity_protect` (Equity Protect + Basket Harvest), `core_orphan_reconcile` and `core_template_placeholder_repair` were unreachable — their call sites live in the monitor loop, which the refactor had relocated, so they did not come across with the engine hunks. |
| **Five modules computed paths by counting parents** | Correct from their old homes, silently wrong from their new ones: autostart could not find `tools/watchdog.py` (refused to arm), `ea_bridge` could not find the EA source (reported every EA stale), `remote/client.py` and `remote/server.py` resolved VERSION/CHANGELOG to `backend/` (so "which commit is this client running" answered unknown), `mt5_native` looked for `mt5_bridge.py` in `backend/src/`. Only two had a failing test; a sweep found the rest. All now walk up for `run.py`. |
| `run.py` configured logging **at module scope again** | The merge kept our block *and* took upstream's deferred `setup_logging()`, so `import run` hijacked the root logger and pytest wrote into the live app's log. |

Also corrected: the comment in `backend/src/config/__init__.py` said the app data
folder must never be `"ForexTrader"` while the code, after upstream's deliberate
revert (`212fd87`), used exactly that. The revert is right — the fork was
promoted to be the only app on 2026-07-24 — but a safety comment that
contradicts its own code is worse than no comment. It now records both halves
and names the condition under which the old hazard returns.

## Still true

Nothing here has gone near `main`, and this branch is still not demo-ready.
Most of the 111 upstream commits touch order placement, closing or sizing.
Porting code that already runs live is not the same as proving the port did not
change it — that is what the Part B session on Simon's demo account is for.

`python -m tools.checks all` has **not** been run: MetaTrader5 is win32-only and
this work was done on macOS. It must run on Windows before anyone calls this
green.
