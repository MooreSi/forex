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

### M1. SQL into repos (~1–2 sessions, safe, mechanical)
230 SQL statements in 67 files sit outside `*repo*.py`. Most are inside the
service that owns them — the fix is moving each query into that service's
existing repo file, same call order, characterization-covered. The counter
is already a shrink-only CI gate; this drives it toward zero. The 13 in
`runtime.py` and 11 in `ea_bridge.py` fold into M3/M2 respectively.

### M2. File splits over 800 LOC (~2 sessions, mechanical)
22 files over the ceiling. About half resolve by other milestones
(trading.py, settings.py, runtime.py shrink via M4/M3). Independent
mechanical splits: telegram `reader.py` (1,037), `ea_bridge.py` (816),
backtest `engine.py` (1,125), remote/sync servers and clients (867–1,196),
`email_service.py` (946), test_signal `signal_generator.py` (1,052) and
`ml_engine.py` (896).
**Decision needed:** `mt5_bridge.py` (1,335) deliberately stays at the repo
root as a subprocess under a different Python — split it in place, or
grant it a permanent exemption?

### M3. Drain the frontend pages (~3–4 sessions, the big one)
13 pages still import the database directly (22 imports). Per page, the
proven four-commit procedure: queries → service repo; data-shaping →
`controllers/<name>/controller.py`; page becomes widgets + controller
calls; registry update. Largest: `trading.py` (3,290), `settings.py`
(3,204), `ai_trade_analysis.py` (1,721), `history.py` (1,613, already
half-drained). Finishing this flips the frontend import contract from
counted to **enforced** — the point where `frontend/` can only see
`controllers/`.

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
