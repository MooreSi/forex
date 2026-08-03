# Where the finish line is

Status as of 2026-08-03, branch `claude/refactor-plan-docs-pjn1hl`.
Suite: **1989 passed, 6 skipped, 0 failed.** All gates green and ratcheting.

## Done — the plan's structural end state is reached

- `forex_trader/` is **gone**. Repo root is the target shape: `backend/`,
  `frontend/`, `run.py`, `mt5_bridge.py`, `mql5/`, `installer/`, `docs/`,
  `tests/`, `tools/`.
- `backend/src/` holds `config/`, `db/`, `utils/`, the service packages,
  `controllers/`, `app.py` (composition root) and `runtime.py`.
- Zero orphaned extractions, zero unwired duplicates.
- The suite is deterministic (fixed clock, cache invalidation registry) and
  runs anywhere.

### M1. SQL into repos — ✅ DONE
230 SQL statements across 67 files → **0 outside the data layer**. Every
statement lives in its service's repo; formerly-atomic multi-statement
blocks are explicit `transaction()` functions. Ratchet pinned at zero.

### M2. File splits over 800 LOC — ✅ mostly done, two items deferred
Backend service splits landed. Still over the ceiling and deliberately so:
- `mt5_bridge.py` (1,335) — runs under a *different Python interpreter*
  (Wine/Windows). **Owner decision** in OPEN_QUESTIONS.md §2.
- `remote/{server,client}.py`, `sync/{server,client}.py` — **deliberately
  not split, and the reason changed.** The recorded rationale ("all four
  rebind module state via `global`") holds for `remote/server.py` only;
  the two sync files have a single singleton `_instance` each. What
  actually blocks the work is that `controllers/remote/` — 2,116 lines of
  licence-token issuance, revocation and admin-machine authority — has
  **zero test coverage**. Splitting untested auth code for a line-count
  target is the wrong trade. Test it first; then the split is mechanical.
  See OPEN_QUESTIONS.md §8.
- The frontend pages remain large; widget-level splits are cosmetic.

### M3. Drain the frontend pages — ✅ DONE
The frontend no longer touches the database: **0 files, 0 imports** (was
13/22). Ratchet pinned at zero.

*Correction found in M5:* this closed the **database** boundary, not the
service boundary — 99 frontend→service imports remain. The new
`frontend-reaches-the-backend-through-controllers` contract measures them.

### M4. Dissolve runtime.py → TradingRuntime — ✅ DONE
**3,052 → 1,310 LOC; 142 → 79 methods.** The class is now
`TradingRuntime` (the old name is kept as a compatibility alias; it
predated the app doing real broker work).

What runtime.py is now: `__init__` (state), `startup`/`shutdown`
(composition), five ctx builders (wiring), the curated facade, and loop
shells that own an asyncio task and delegate one iteration. 909 lines of
method, 401 of imports and class scaffolding.

Bodies relocated, each with its own wiring tests:
`scan_messages` → `services/signals/scan_messages.py` ·
`sync_closed_mt5_positions` → `services/broker/position_sync.py` ·
the monitor cycle → `services/positions/monitor_cycle.py` ·
`start_bridge_process` → `services/broker/bridge_process.py` ·
the bot loop → `services/telegram/bot_loop.py` ·
the TP-ladder loop → `services/positions/tp_ladder_loop.py` ·
the node-role checks → `services/cluster/node_roles.py` ·
plus the AI-refresh, bridge-watchdog and research loops.

**It does NOT meet the <400 LOC target, and will not.** That figure assumed
full dissolution. The plan instead chose a **curated facade** — ~39
intentional public methods binding bridge/caches in one place — because
full dissolution meant ~90 call sites each hand-carrying eight
collaborators, which is precisely the drop-a-collaborator failure mode that
produced the dead code Phase 0 found. With that design, ~1,300 is the floor:
401 lines of imports/scaffolding, ~200 of ctx builders, the rest facade.
The 800-line ceiling is likewise not met for this file. That is a design
consequence, recorded rather than papered over.

Replaced tooling: `delegation_checker.py` had been **vacuous since the
restructure** (it globbed a deleted directory and reported success). It is
deleted; `facade_audit.py` is its live successor.

### M5. Formal import contracts — ✅ DONE
Five named contracts in `tools/refactor_audit/import_contracts.py`, enforced
by the suite. Two at **zero** (`controllers-never-import-repos`,
`frontend-never-imports-the-database`); three baselined shrink-only
(frontend→controllers 99, nicegui-in-backend 3, utils/config upward deps 12).
Each carries a rationale, and a test asserts the rationale is more than a
restatement of the rule.

Deviation: the plan named import-linter. This uses the repo's own ratchet
idiom instead — same `--check`/`--update-baseline` interface as the other
gates, no new runtime dependency, and baselines, which import-linter lacks.

### M7. Expert Tunables — ✅ DONE
`services/risk/expert_params.py` — a declarative catalogue of the 12 Tier-A
constants, stored as a DB override merged over defaults, node-synced,
cache-invalidated on env switch, clamped to declared safe ranges. Rendered
generically at **Settings → Expert Tunables** with per-row reset.

**Every default is byte-identical to the constant it replaced**, asserted
per-parameter. Nothing trades differently until a dial moves. Ranges and
the Tier-A list want owner review — OPEN_QUESTIONS.md §3.

### Small items — ✅ DONE
- **Installer**: was packaging `forex_trader\*` and icons from a deleted
  directory, so it had been **unbuildable since the restructure** (Inno
  fails at compile time on a path that matches nothing) and nothing said
  so. Now ships `backend/`, `frontend/`, `run.py`, `VERSION`,
  `CHANGELOG.md`, with a test asserting every packaged path resolves.
- **transaction() wrapping**: 8 → 5. The three in the main trading DB are
  converted. The remaining five are the schema builder plus four in the
  per-engine research DBs, which use their own non-nesting `_conn()` —
  fixing those means changing that layer, not renaming a call.
- **Frontend verification**: new `tests/frontend/` — every page module
  imports and exposes a renderer (34), and the app boots, binds and serves
  HTTP with no traceback.

## Remaining

### M6. The demo-gated work — **needs your brother**
Re-extract the CloseTradeContext cluster. This **rewrites order-closing
code**, so per the standing safety rule it waits for (a) explicit sign-off
and (b) a session against a **demo** MT5 account watching trades open and
close correctly. No real account, ever.

Throughout every batch above the close path was left byte-identical —
`_make_close_trade_ctx`, `close_trade` and `record_close` were renamed at
most, never reshaped — and `test_close_trade_characterization.py` passes
unmodified as the witness.

### Open decisions
See **OPEN_QUESTIONS.md** — mt5_bridge.py's fate, the Expert Tunables
ranges, money-as-floats (decide before M6 touches trading maths), and Q3
(eyeball the new Telegram trade sizes, which changed when the lot-sizing
fork was fixed).

### Opportunistic
119 local `fresh_db` fixture copies still to collapse into the canonical one
in `tests/conftest.py`; done on files each batch touched, not exhaustively.
