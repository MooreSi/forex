# Backend Foundation — gd_copy_signal migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-19

## 👋 Picking this up (agents start here)

1. **Read the plan** — `SUMMARY.md` for the plain-English digest; this hub for the index +
   decisions.
2. **Check [PROGRESS.md](PROGRESS.md)** — the shared status log. See what's done / in progress /
   free.
3. **Claim your task** in PROGRESS.md: set its row to `in progress`, add your name + date under
   Owner.
4. **Do the work** from the task file (`0N0-*.md` — tests-first + acceptance).
5. **Update PROGRESS.md** as you go — `done` (with commit) or `blocked` (say why).

Gates: tests first per the `test` skill; **explicit user sign-off before implementing 050
(the only task with a real-money/MT5 surface)**; conventions per `backend-conventions` /
`database-conventions`, translated from their TypeScript/Express source material to this
codebase's actual Python/NiceGUI/asyncio shape — see "Adapting the conventions" below.

## What we're building & why

This is Phase 1 of restructuring the FOREX Trader backend (originally requested: `src/`
layout, service/repo layers, a reliable ORM, transactional DB calls, files under 800 LOC).
It runs entirely inside `forex-refactor2` — a full fork of the live app, isolated in its own
directory and GitHub repo — so the live app at `/Users/simon/Documents/FOREX` (currently
trading, including tonight's Asian session) is never touched.

Rather than attempt the whole ~64,000-line application at once, this pack proves the pattern
on the smallest of the four signal engines, `gd_copy_signal` (1,295-line `engine.py`,
752-line `database.py`, 3,815 lines total across the module) before applying it to the much
larger `core/engine.py` (10,065 lines) or the other engines. If the approach doesn't fit
cleanly here, that's cheap to discover and adjust before committing to a bigger engine.

The `backend-conventions` and `database-conventions` skills consulted for this plan are
written for a different stack (Express + TypeScript, dual SQLite/PostgreSQL, a stock-
watchlist example app) — there is no literal translation for a Python/NiceGUI codebase. What
carries over is the *shape*: a repo/adapter layer that owns all SQL and wraps multi-statement
writes in real transactions, a thin service/orchestrator layer above it, extraction ordered
pure-functions-first then writes-last, and firm size budgets. File suffixes below use `.py`
and Python naming, not the `.ts` vocabulary the skills describe.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live shared status log |
| [SUMMARY.md](SUMMARY.md) | Plain-English digest of every change |
| [QUESTIONS.md](QUESTIONS.md) | Decisions to confirm / answered, including items carried forward from the earlier (superseded) `forex-refactor` investigation |
| [010-data-access-foundation.md](010-data-access-foundation.md) | Shared `DbAdapter` + transaction wrapper — new code, TDD from scratch |
| [020-characterize-gd-copy-current-behavior.md](020-characterize-gd-copy-current-behavior.md) | Characterization tests locking in gd_copy_signal's current behavior before anything is touched |
| [030-migrate-gd-copy-repo-layer.md](030-migrate-gd-copy-repo-layer.md) | Rebuild the data layer on the new adapter, with real transactions |
| [040-extract-gd-copy-service-layer.md](040-extract-gd-copy-service-layer.md) | Split `engine.py` into a thin service + sub-flow files, each under 800 LOC |
| [050-demo-account-validation.md](050-demo-account-validation.md) | Sign-off gated — end-to-end proof against a demo MT5 account |

## Decisions locked with the user (2026-07-19)

| Decision | Choice | Source |
|---|---|---|
| Repo | `forex-refactor2` supersedes the earlier `forex-refactor` attempt (Phase 0 fork + hand-built docs there are abandoned; trivial to redo, no real code was written) | user |
| Data-layer approach | Repo/adapter pattern (parameterized SQL behind a typed interface + transaction wrapper) — not a traditional object-relational ORM | user |
| First engine to migrate | `gd_copy_signal` — smallest at 1,295 lines (`engine.py`) | user |
| Phase 1 scope | `gd_copy_signal` only — DB layer + service extraction. `core/engine.py`, `breakout_signal`, `test_signal`, UI pages, the MQL5 EA, and the sync protocol are explicitly out of scope for this pack | user |
| Sign-off gating | Only tasks touching a live/demo MT5 order path need per-task sign-off (that's 050); pure data/service work (010-040) proceeds under TDD without pausing per task | user |
| Live app safety | The original `/Users/simon/Documents/FOREX` app and its `MooreSi/forex` GitHub repo are never edited, restarted, or deployed to as part of this work | user, safety-critical |

## Building blocks we reuse (do not rebuild)

| Need | Existing code |
|---|---|
| Pattern-detection / level-detection logic | `forex_trader/gd_copy_signal/ict_patterns.py`, `level_detector.py` — already reasonably sized and domain-grouped; no planned changes |
| ML scoring | `forex_trader/gd_copy_signal/ml_engine.py` (537 lines) — untouched by this pack |
| Signal construction | `forex_trader/gd_copy_signal/signal_generator.py` (183 lines) — untouched by this pack |
| VIP research/correlation source data | `forex_trader/gd_copy_signal/telegram_research.py` (360 lines) — untouched by this pack |
| Decomposition ordering | `backend-conventions` §7: pure functions first, completion/tracking handlers next, transaction-wrapped writes last |
| Transaction pattern | `database-conventions` §3: `db.transaction()` wrapping multi-statement writes, translated to a Python async context manager |

## Out of scope

- `core/engine.py` (10,065 lines), `breakout_signal/`, `test_signal/` — later packs under `refactor/`, once this one proves the pattern.
- `ui/pages/*.py` restructuring — deferred; scope decided in a later pack.
- Modifying `mql5/ForexTraderBridge.mq5` or the live EA/bridge config — never in scope; 050 only *tests against* a demo account.
- Consolidating the 4 engines' separate SQLite databases into one — open question, deferred (see QUESTIONS.md).
- Fixing `gd_copy_signal`'s money columns being stored as SQLite `REAL`/float (a real defect per `database-conventions` §6) — deferred because fixing it ripples into the UI, sync protocol, and Telegram alerts that read those columns today, all outside this pack.
- Anything touching the live `/Users/simon/Documents/FOREX` app or the `MooreSi/forex` remote.

## Open questions

Answered items stay here annotated. Full interviews live in QUESTIONS.md.

- DB consolidation across the 4 engines — still open (current default: keep separate per-engine DBs, revisit once more than one engine is migrated).
- UI scope for future packs — still open (current default: backend-only for now).
- Cutover criteria ("complete and all testing is done") — still open (current default: this pack's own Acceptance criteria per task, plus 050's demo validation, are the bar for *this* engine; app-wide cutover criteria need a separate decision once more engines are done).
- Multi-tenant / KeyGen distribution scope — still open (current default: not designed for now, revisit if distribution plans firm up).
- Sync protocol (Mac ↔ VPS) timing — still open (current default: untouched until a dedicated later pack).
