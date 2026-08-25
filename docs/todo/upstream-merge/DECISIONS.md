# Upstream merge — the decision log

Merging `MooreSi/forex` `main` (111 commits, 2026-07-24 → 2026-08-24) into the
refactored tree on `claude/upstream-merge-and-handover-answers`.

**Shared history, so this is a true merge.** `forex-update/main` (`f0f0991`) is
the fork point and a direct ancestor of `forex/main`. `forex`'s
`ea-panel-signal-and-orphan-reconcile` branch is **fully contained** in its
`main` (0 commits ahead) — nothing separate to merge.

Shape: **one merge commit**, resolutions on top. Every upstream commit and its
authorship is preserved, and `forex/main` stays a true ancestor so the next sync
is cheap.

## The conflict surface

| Category | Count | How it was handled |
|---|---|---|
| Content conflicts | 51 files / 106 hunks | 23 import-only (scripted), 19 small, 64 substantive (by hand) |
| File location | 30 | Git's directory-rename detection placed new upstream modules correctly; verified and staged |
| Modify/delete | 10 | Case by case below |
| Rename/delete | 6 | Case by case below |
| Add/add | 2 | By hand |

Git's rename detection carried far more than expected: of 235 upstream files,
only **five** landed in the dead `forex_trader/` layout and needed re-homing.

## The module map

Import rewriting is **derived, not guessed**: 178 mappings read out of the
refactor's own `R`-rename records (`git diff --name-status -M50%` from the fork
point), plus 34 matched by basename where this merge relocated a new upstream
file, plus 7 hand-checked entries for modules the refactor dissolved. 215 total.
Stored at `module_map_full.json` in the session scratchpad; regenerate rather
than hand-edit.

## Decisions on the deletion conflicts

### Licence: accept upstream's deletion (Q005 #2, Q007 #1)

`keygen.py`, `client.py`, `jwt_public.pem`, `public.pem`, `server.crt` are all
**deleted**, per upstream `7251656`. The shared-secret HMAC keygen is replaced by
`verify.py` (Ed25519, public key only); the REST/JWT flow was dead code
`guard.py`'s `enforce()` never called.

Consequence tracked: `tools/generate_debug_licence.py` imported the deleted
keygen and must be rewritten to *request* a licence rather than mint one
(Q007 #1). `guard.py` and `remote/server.py` are re-homed by upstream itself.

### Edge page: accept upstream's deletion

`frontend/pages/edge_dashboard.py` goes. Upstream `152f3df` removed the Edge page
deliberately as a product decision.

### `core_mt5_position_sync.py`: keep OUR version — this one was a trap

Git's rename detection matched upstream's `forex_trader/core/core_mt5_position_sync.py`
onto our `backend/src/services/broker/position_sync.py`. **They are different
modules with different lineage.** Upstream's is the 312-line unwired duplicate
that `2847e32` deleted here (imported by nothing, then and now — verified against
`upstream/main`); ours is the later re-extraction of the *live* inline copy out
of `engine.py` (`38eb439`).

Upstream's two changes to it (`8d20bd3`, `ebd164b`) were made **in parallel to the
live inline copy in `engine.py`** — `ebd164b`'s own message says it fixed "both".
So those behaviours must reach us through the `engine.py` re-homing, **not**
through this file. Taking upstream's side here would have merged a dead
duplicate over a live module.

### `reversal_engine/database.py`: accept our deletion

Dead clone on both sides — referenced only in comments upstream, imported
nowhere. `da117b6` deleted it here as one of three dead per-engine clones
(3,384 LOC). Its two upstream commits (`cc01f5e`, `b7651f1`) **also** wrote to the
live `reversal_engine_repo.py`, which merges normally, so nothing is lost.

### `tests/core/test_mt5_position_sync_surface.py`: accept our deletion

It drove the dead duplicate above. `2847e32` removed only the surface tests of
deleted functions and kept every characterization test.

### `tests/core/test_bot_commands_readonly_characterization.py`: RESTORE upstream's

Ours deleted a **gutted husk** (`6c52279`: "module docstring + fixtures, zero
`def test_`"). Upstream's version is a real 268-line, 40-assert test extended by
three commits. Restoring it costs one import rewrite: it drives
`SimulationEngine`, which survives as the compatibility alias at
`backend/src/runtime.py:1310` (`SimulationEngine = TradingRuntime`).

Deleting a test that still knows something would breach CLAUDE.md rule 2.

## The five files that needed manual re-homing

A naive three-way merge was **rejected** for these. `runtime.py` is 1,310 lines
against a 3,165-line base because ~1,855 lines were relocated into other modules;
`git merge-file` produced 2,742 lines, resurrecting relocated code as duplicate
implementations. That is precisely the failure mode CLAUDE.md's closing section
describes. Upstream's changes are therefore routed **hunk by hunk** to whichever
module now owns that code.

| Upstream path | Now lives at | Upstream hunks |
|---|---|---|
| `core/engine.py` | `backend/src/runtime.py` (+ relocated loop bodies) | 30 hunks / 34 methods |
| `core/database.py` | `backend/src/db/database.py` | 5 |
| `core/core_profit_sync.py` | `backend/src/services/trading/profit_sync.py` | 2 |
| `ui/pages/trading.py` | `frontend/pages/trading/` (10-module package) | 17 |
| `reversal_engine/database.py` | deleted (dead clone, above) | n/a |

## Money-touching: this merge needs a demo session

CLAUDE.md: *stop and ask when the change touches order placement, closing or
position sizing.* Most of the 111 upstream commits do. The mitigating fact is
that this is **porting code already running live**, not writing new behaviour —
but the port itself can silently change behaviour, which is the risk that makes
the demo mandatory rather than optional.

This branch is therefore a **candidate for review and a demo session**, never a
fast-track to `main`. Nothing here has been merged to `main` on either repo.

---

# Part 2 — the resolutions, as landed

## Where upstream's behaviour won

Every one of these is a fix already running in Simon's live app, ported here:

| Area | What upstream fixed |
|---|---|
| `ai_signal_fallback` | `modify_order()` reports broker rejection as a returned `{"error": ...}` dict, not an exception, so a rejected SL move was recorded as applied. Confirmed live 2026-07-28 (ticket 1663956102): the app reported "4037.12 -> 4027.12" applied while the position kept running on its original, much wider stop. |
| `risk/governor` | The R:R bypass now covers every IME channel, not just two hardcoded names. Every GOLD DIGGERS INSTITUTIONAL signal since 2026-08-05 12:47 was being rejected at the 0.75:1 floor while its sibling channel kept trading. |
| `broker/position_sync` | `reason` was blindly prefixed, producing "MT5_MT5_close". |
| `ea_bridge` | Anchor-leg fills reached nothing at all: the row kept `mt5_ticket=0`/`entry_price=0` for life, so close messages quoted ticket 0 and a P&L from a $0 entry — **-$16086 reported on a real -$15.63 loss** (2026-07-29). Also: a sibling leg's close is no longer recorded as the parent's. |
| `news_calendar` | The blackout had never fired on live data — the feed names its currency field `country` and both parsers read `currency`. See Q004. |
| `backfills` | `_gd2_instant_entry` ran on **every boot**, silently re-enabling IME within seconds of it being turned off, making it impossible to disable on a gd2 channel at all. Now marker-gated to run once. |
| `open_trade` | The trade row stored the signal's own tp1..tp8 while the EA ran the template's — the alert, the UI and TP Safety Net all reported levels nobody was trading. |
| `signals/resolution` | Sig Guard gained a distance arm (`guard_pips`), so a genuinely separate setup further down the chart no longer counts as stacking. |

## Where the refactored structure won

Upstream's raw SQL was re-expressed through the repo layer rather than reverted:

- `trade_repo.insert_trade_and_activate_signal` gains `grid_legs_total` / `initial_sl` / `initial_risk`.
- `trade_repo.insert_realigned_limit_entry` gains the realised-R seed.
- `broker_repo.apply_pending_fill` gains the realised-R seed.
- `broker_repo.claim_grid_leg_fill` becomes `claim_template_leg_fill(... lots, kind ...) -> (row, is_first)`, absorbing upstream's anchor-leg support and its `{}`-is-falsy fix.
- `signals_repo.template_trade_open_for` becomes `template_trade_open_entries`, returning entry prices so the service can apply `guard_pips`.
- `reversal_engine_repo.fetch_ml_outcome_rows` gains `sl_dist` / `net_pnl_dollars` for the realised-R label.
- Frontend pages keep their controller calls; `reversal_panel`'s new `_get_realised_pnl` moved down into `panel_data` + `engines_controller.reversal_realised_pnl()`.

Schema evolution went where the refactor put it: upstream's 57 new columns became **numbered registry steps 13-28** (append-only, upstream's own order and grouping preserved), the new `tg_signal_snapshots` table went into `schema_sql.py`, and the three one-off heals in upstream's `_apply_schema` tail became named entries in `backfills.py`. Verified: **192 migration statements apply cleanly to a fresh legacy-shape database**, and every column the merged code writes is present.

`core/engine.py`'s 30 hunks were routed method by method into `runtime.py` rather than three-way merged — see the note above on why. Upstream's five new runtime loops arrived with it; `_ea_link_watchdog_loop` had to be carried over by hand (it was started but undefined). `ui/pages/trading.py`'s 12 hunks routed cleanly into the 10-module package, every one matching exactly one module.

`core_orb_report.py` was **rebuilt** upstream (classic Opening-Range-Breakout methodology, volume profile removed), so both halves were rebuilt from upstream and re-split along the refactor's read-only/execute boundary.

## Changes made to tests, and why

Two, both because upstream deleted the subject:

1. `tests/utils/test_news_debug.py` patches `_from_mt5` / `_from_finnhub` / `_from_forexfactory`. Upstream deleted all three (two were dead, the third held the field-name bug). **Not yet reconciled — see Open items.**
2. `frontend/pages/history.py` gained a thin `_broker_ts_to_uk_date` delegate so upstream's `tests/ui/test_history_session_attribution.py` can reach it at page level; the logic itself stays in the service.

3. `tests/core/test_bot_commands_readonly_characterization.py` — **restored, then
   re-deleted, and that reversal is the honest answer.** It was restored on the
   reasoning that ours had deleted a gutted husk while upstream's version was a
   real 268-line, 40-assert test. Running it settled it: every one of its 22
   tests drives `SimulationEngine._cmd_risk` / `_cmd_strategy` / `_cmd_balance` /
   `_cmd_status`, and the refactor moved those methods off the engine entirely
   (`TradingRuntime` has none of them). The behaviour is covered by
   `tests/core/test_bot_commands_readonly_surface.py` — **28 tests, all passing
   against the merged tree** — which is exactly what commit `6c52279` claimed
   when it deleted the husk. The subject was relocated by design; the coverage
   was not lost.

## Known-failing gates, deliberately (Simon's call, 2026-08-25)

The shrink-only LOC ratchet is breached by files upstream spent a month adding to:

| File | Cap | Now |
|---|---|---|
| `frontend/pages/settings.py` | 3,112 | ~3,490 |
| `frontend/pages/history.py` | 1,416 | ~1,770 |
| `backend/src/runtime.py` | 1,310 | ~1,550 |
| `cluster/remote/server.py` | 1,196 | ~1,250 |
| `frontend/app.py` | 1,633 | ~1,760 |
| `frontend/pages/reversal_panel.py` | 804 | ~960 |
| `frontend/pages/chart.py` | 839 | ~945 |
| `reversal_engine_repo.py` | 809 | ~845 |

Decision: land the merge as a faithful port with these documented, and decompose into new modules as separate reviewable commits. **The baseline was NOT lowered.** Mixing "port upstream behaviour" with "restructure into modules" in one commit would make both unreviewable, and the Part B demos need a faithful port to demo against.

The frontend also picks up new `backend.src.db` imports from upstream's pages (`history.py` especially), regressing the controller-boundary contract. Same treatment: recorded, not hidden.

## Open items

- Reconcile `tests/utils/test_news_debug.py` with the deleted source ladder.
- Decompose the eight over-cap files; restore the frontend/db boundary.
- `KeyGen/forex_admin.py` (outside this repo, on Simon's machine) still imports `forex_trader`, so the admin button will be hidden on this build until its imports are updated.
- Re-run `python -m tools.checks all` on Windows: MetaTrader5 is win32-only and the four structural gates, the orphan gate and the coverage ratchet were not exercised on the Mac used for this merge.
