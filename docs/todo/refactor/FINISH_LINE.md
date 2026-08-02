# Where the finish line is

Status as of 2026-07-31, branch `claude/refactor-plan-docs-pjn1hl`.
Suite: 2005 passed, 5 skipped, 0 failed. All CI gates green and ratcheting.

## Done — the structural move is complete

- `forex_trader/` is **gone**. Repo root is the target shape: `backend/`,
  `frontend/`, `run.py`, `mt5_bridge.py`, `mql5/`, `installer/`, `docs/`,
  `tests/`, `tools/`.
- `backend/src/` holds exactly `config/`, `db/`, `utils/`, 16 service
  packages under `services/`, `controllers/`, `app.py` (composition root),
  `runtime.py` (the engine, relocated verbatim).
- Zero orphaned extractions, zero unwired duplicates, every engine method
  with an extracted twin delegates to it.
- The suite is deterministic (fixed clock, cache invalidation registry) and
  runs anywhere.
- Live defects fixed along the way: the Telegram lot-sizing fork (Max Risk
  per trade % now applies on every entry path), the demo/live switch serving
  stale risk settings for 10s, a non-atomic signal insert.

## Remaining — six milestones to the plan's end state

Ordered by the sequence that makes each one cheapest. "Session" ≈ one long
working day of Claude time.

### M1. SQL into repos — ✅ DONE (2026-08-01, four batches, commits 4889f69..590af45)
Was 230 SQL statements in 67 files; now 31 in 8. **Backend services carry
zero inline SQL** — every statement lives in its service's repo, with
formerly-atomic multi-statement blocks as explicit `transaction()`
functions. The 31 that remain are runtime.py's 13 (fall to M4), the
frontend pages' 17 (fall to M3, where each becomes a controller call), and
one docstring false-positive. The ratchet baseline is tightened to match,
so none of it can come back.

### M2. File splits over 800 LOC — backend services DONE, 16 files remain
Five splits landed 2026-08-01 (email_service, telegram reader,
backtest engine, signal_generator, test_signal ml_engine — plus ea_bridge
dropped under the ceiling via M1). Of the 16 still over:
- 9 are frontend pages / frontend app → resolve in **M3**'s page drains.
- `runtime.py` → **M4**; `database.py` → the shim split after the test
  fixture migration.
- `remote/{server,client}.py`, `sync/{server,client}.py` (867–1,196):
  **deliberately deferred** — all four keep module-level state that is
  REBOUND via `global` (e.g. `_allowed_tokens = json.load(...)`), so a
  naive split would silently fork that state between modules. They need a
  small state-module refactor first (attribute access instead of module
  globals), a careful pass on a security-sensitive path.
**Decision needed:** `mt5_bridge.py` (1,335) deliberately stays at the repo
root as a subprocess under a different Python — split it in place, or
grant it a permanent exemption?

### M3. Drain the frontend pages — ✅ DONE (2026-08-01, four batches)
**The frontend no longer touches the database at all: 0 files, 0
imports** (was 13 files / 22 imports). Every page and the app shell now
go through `backend/src/controllers/` — dpm, telegram, settings,
remote_node, chart, engines (shared by the three panels), ai_analysis,
history (which also took over the ticket-map builders and the
trade-source/channel label helpers), and trading. Same queries, same
DB-worker-thread dispatch, plain dicts back. The ui_db ratchet baseline
is now **zero**, so any new frontend DB import is an instant CI failure —
the boundary enforces itself. (The pages still exceed 800 lines; the
widget-level file splits are cosmetic and can ride along with future page
work.)

### M4. Dissolve `runtime.py` into TradingRuntime (~2 sessions, after M3)
3,143 LOC today. 110 of its 142 methods are pure one-line wrappers
(861 LOC) — but 105 are the API the pages and callbacks reach *through the
engine object*, so they can only be deleted once M3's controllers exist and
`app.py` wires callbacks to services directly. End state: a task
supervisor under 400 LOC holding the ~20 asyncio task handles and mutable
caches, everything else in services.

### M5. Formal import contracts (~half a session, after M3)
The gates exist as shrink-only counters. This turns them into named,
enforcing contracts (import-linter): frontend→controllers only; no nicegui
in backend; controllers never import repos; signals never import broker;
utils/config import nothing.

### M6. The demo-gated work (needs your brother, then ~1 session)
Re-extract the CloseTradeContext cluster — the five modules deleted in the
audit because their extractions were built on a broken partial context.
This **rewrites order-closing code**, so per the standing safety rule it
waits for: (a) explicit sign-off, (b) a session against a **demo** MT5
account watching trades open and close correctly. No real account, ever.

## Small items, any time

- **Installer refresh**: `installer/FOREX_Trader_Setup.iss` still packages
  `forex_trader\*` and icons from `forex_trader\ui\` — it packages nothing
  useful now. Needs a pass to ship `backend/`, `frontend/`, `run.py`,
  root `VERSION`/`CHANGELOG.md`.
- 8 multi-write functions not yet in `transaction()` (4 files, gated,
  shrink-only).
- Test fixture migration: 119 local `fresh_db` copies collapse into the
  canonical `tests/conftest.py` one opportunistically as files are touched.
- `QUESTIONS.md` (phase-0-audit): Q3 (eyeball the new Telegram trade
  sizes), Q7 #10 (money stored as floats — decide before M6 touches
  trading maths), Q8 (ratify the two repo conventions).

## The honest total

Roughly **8–10 more sessions** of this pace to the plan's full end state,
plus one demo-account sitting for M6. M1+M2 are safe and immediate; M3 is
the bulk of the remaining effort; M4/M5 fall out quickly once M3 lands.
