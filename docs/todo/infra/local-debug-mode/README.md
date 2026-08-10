# Local debug mode — offline fakes, login, banner, e2e

**Spec:** [SPEC.md](SPEC.md) (in this pack)
**Status:** planning (pre-implementation)
**Domain:** infra
**Touches money:** YES — task 020 only (the `_make_bridge` seam in `runtime.py` + bridge-subprocess
skip in `run.py`). `/safe-change` governs it; owner sign-off + demo session required before Done.
No other task edits order, sizing or close code.
**Created:** 2026-08-10

## 👋 Picking this up (agents start here)

1. **Read the rules first** — [CLAUDE.md](../../../../CLAUDE.md) and
   [docs/system/rules/10-golden-rules.md](../../../system/rules/10-golden-rules.md). This app places
   real orders with real money.
2. **Read the plan** — the anchor spec for Problem/Goal/what-must-NOT-change; this hub for the
   index + decisions; `SUMMARY.md` for the plain-English digest; `REVIEW.md` for the mapped
   integration surface every task builds on.
3. **Check [PROGRESS.md](PROGRESS.md)** — the shared status log.
4. **Claim your task** in PROGRESS.md: set its row to `in progress`, add your name + date.
5. **Do the work** from the task file — tests first, watch them fail, then implement.
6. **Update PROGRESS.md** as you go.

Gates: `/safe-change` before task 020 · `/add-tunable` for user-editable numbers ·
`/split-file` if a target file is over 800 lines (`frontend/app.py` at 1633 lines already is —
see task 060/070 notes) · `python -m tools.checks all` before every commit.

## What we're building & why

Darren is refactoring this system for Simon, who holds every credential — MT5 account, Telegram
API/bot, Anthropic key, licence. The refactor has **never been booted** by the person doing it:
there is no way to run the app without those credentials, because every dependency is called
directly with no interface behind it. Before the refactor goes back to Simon, we need to prove
the whole system alive locally.

The shape: a `debug_mode` config flag (env `FOREX_DEBUG_MODE` or `config.yaml`) that swaps each
external dependency for a coded fake at the composition root — a fake MT5 bridge streaming
synthetic ticks and filling orders against an internal ledger, a fake Telegram reader replaying
scripted signal messages through the real parser, canned news/AI/email, and a locally generated
(real, verified — **not** bypassed) licence key. The frontend shows an unmissable banner when
debug mode is on. Separately, the dashboard gets a real username/password login in both modes —
today it has none. A new `tests/e2e/` suite then drives signal → parse → place → manage → close
entirely offline.

The fakes are written as named adapter seams, not test hacks: the same ports accept future real
integrations (another broker, other signal sources), which Darren and Simon both want anyway.

## What must NOT change

The anchor spec's section is authoritative; the lines that constrain these tasks:

- The frozen close path is untouched. The fakes *receive* its calls.
- `_make_bridge` with debug off: identical branches, defaults, config keys; runtime shape-guard
  tests pass unmodified.
- `guard.enforce()` is not edited — debug passes it with a valid key, never around it.
- `debug_mode` defaults off; a config.yaml without the new keys behaves exactly as today.
- Debug mode never opens the demo/live DB files — it gets `forex_trader_debug.db`.
- The four import contracts stay at zero; no ratchet baseline rises.

## Doc index

| Doc | Contents |
|---|---|
| [SPEC.md](SPEC.md) | The anchor spec: Problem / Goal / what must NOT change / test plan |
| [PROGRESS.md](PROGRESS.md) | Live shared status log |
| [SUMMARY.md](SUMMARY.md) | Plain-English digest for Simon (owner-facing) |
| [QUESTIONS.md](QUESTIONS.md) | Decisions to confirm — answer inline before building |
| [REVIEW.md](REVIEW.md) | Evidence: the mapped external-dependency surface (paths:lines) |
| [BAR.md](BAR.md) | Screen bar for the login page + debug banner (draft — Darren must edit) |
| [010-debug-config.md](010-debug-config.md) | `debug_mode` flag, `is_debug()`, debug DB isolation |
| [020-fake-mt5-bridge.md](020-fake-mt5-bridge.md) | `FakeMT5Bridge` + the `_make_bridge` seam (MONEY) |
| [030-fake-telegram.md](030-fake-telegram.md) | Fake signal reader; alerts/bot no-op in debug |
| [040-fake-news-ai-email.md](040-fake-news-ai-email.md) | Canned news calendar, AI provider, email |
| [050-debug-licence.md](050-debug-licence.md) | Locally generated valid licence key; cluster stays off |
| [060-dashboard-login.md](060-dashboard-login.md) | Username/password login, both modes |
| [070-debug-banner.md](070-debug-banner.md) | Frontend banner when debug mode on |
| [080-e2e-offline.md](080-e2e-offline.md) | `tests/e2e/`: signal → open → manage → close on fakes |
| [090-docs.md](090-docs.md) | CHANGELOG, config.yaml.example, in-app help, spec checklist |

## Roadmap

| # | Task | Depends on | Money | Ships with |
|---|---|---|---|---|
| 010 | debug-config | — | no | — |
| 020 | fake-mt5-bridge | 010 | **YES** | — |
| 030 | fake-telegram | 010, 020 | no | — |
| 040 | fake-news-ai-email | 010 | no | — |
| 050 | debug-licence | 010 | no | — |
| 060 | dashboard-login | — | no | — |
| 070 | debug-banner | 010 | no | 060 (same header area of `frontend/app.py`) |
| 080 | e2e-offline | 020, 030, 040, 050 | no | — |
| 090 | docs | all above | no | — |

010→050 and 060 can run in parallel sessions; 080 needs the offline boot complete; 090 is last.

## Decisions locked with the user (2026-08-10)

| Decision | Choice | Source |
|---|---|---|
| Pack shape | Flat pack, 010–090 | user (interview) |
| Login scope | Real login shipping in BOTH modes, not debug-only | user (interview) |
| Fake scope | All of: MT5+prices+fills, Telegram in/out, news, licence/cluster-off, AI | user (interview) |
| Licence approach | Generate a *valid* key via existing `keygen.py`; never edit `enforce()` | golden rule "no bypass" — **still needs Simon's sign-off, see QUESTIONS.md #1** |
| Debug DB | Own file `forex_trader_debug.db`, never demo/live | safety inference — confirm in QUESTIONS.md #5 |

## Building blocks we reuse (do not rebuild)

| Need | Existing code |
|---|---|
| Bridge selection seam | `backend/src/runtime.py:170-179 _make_bridge(config)` — add the third branch here |
| The bridge surface to implement | 19-method table in [REVIEW.md](REVIEW.md) §1 (`mt5_client.py:129-404` / `mt5_native.py:133-338`) |
| Config env-over-yaml pattern | `backend/src/config/__init__.py:74-75 _e()` |
| DB swap precedent | `backend/src/db/connection.py:62 set_db(adapter)` — "e.g. a fake/in-memory one for tests" |
| Engine injection precedent | `tests/conftest.py:103 make_engine` (its docstring already assumes `_bridge=FakeBridge()`) |
| Sim balance ledger | `backend/src/services/trading/sim_account.py` — fake account can mirror its conventions |
| Signal entry point | `services/signals/scan_messages.py:88` + reader buffer `reader_listener.py:229` |
| Password hashing | `services/cluster/remote/auth.py:30,40,55` (scrypt set/verify/is-set) |
| Licence key generation | `config/licence/keygen.py:21 generate_licence_key` |
| Header row for the banner | `frontend/app.py:893-911` |
| Existing per-test fake bridges | 12+ `_FakeBridge` classes in `tests/core/` (REVIEW.md §10) — consolidate onto the new fake |

## Out of scope

- Reconciliation / idempotency (SPEC-002, SPEC-003 own those).
- Backtesting or strategy evaluation on the fake stream.
- Multi-user auth, roles, HTTPS on the dashboard.
- Faking the EA TCP bridge's MQL5 side — in debug the EA bridge simply stays disabled.
- Fixing the review findings in `docs/reviews/2026-08-08/` (separate work; the fakes must not
  quietly "fix" behaviour the review documents).

## Open questions

Full write-ups in [QUESTIONS.md](QUESTIONS.md); the short list:

- Debug licence key: Simon's sign-off on generating a valid local key (default: proceed for
  local dev only, key expires in 30 days).
- Scenario format for fake ticks/signals (default: JSON files under `tools/debug_scenarios/`).
- First-run password setup flow (default: setup page on first load when no hash exists).
- Does the fake model slippage/partial fills? (default: no — exact fills, error injection only.)
- Confirm debug DB isolation approach (default: dedicated `forex_trader_debug.db`).
