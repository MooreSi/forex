# Full System Review — 2026-08-11

A read-only review of the whole system by six independent passes, three days after the
2026-08-08 review and after the stage-1/stage-2 remediation sweep landed. Nothing was run
except cheap gates and greps; MT5 was never touched; no code was changed. Each pass
re-verified the 08-08 findings **in the code** (not in docs) and then did a fresh
unbiased sweep. This file is the synthesis.

| Report | Scope |
|---|---|
| [risk-review.md](risk-review.md) | The money path — send, sizing, close, halts, the new debug mode. |
| [backend-review.md](backend-review.md) | Architecture, layering, dead code, duplication, async hygiene. |
| [data-review.md](data-review.md) | Migrations, backups, atomicity, reconciliation, idempotency. |
| [security-ops-review.md](security-ops-review.md) | Binding, the new login, update channel, licence, CI. |
| [frontend-review.md](frontend-review.md) | Structure, the restructure state, code quality. |
| [testing-review.md](testing-review.md) | Gates, ratchets, CI reality, coverage floors. |

Three topical reviews from earlier today sit alongside and are complementary:
[frontend-onboarding-review.md](frontend-onboarding-review.md),
[testing-design-review.md](testing-design-review.md), and
[handoff-readiness-review.md](handoff-readiness-review.md) — note the last was written by
the same agent that did the sweep; this review was not.

---

## The honest verdict on the refactor

**The refactor is real, and it is honest — but it deliberately hasn't touched the part
that loses money yet.** Since 08-08 the *infrastructure* moved from "sloppy AI-coded"
to genuinely disciplined: the guardrails that used to pass vacuously are now fail-closed
and pinned by negative-control tests; migrations are a real numbered, stamped, fail-closed
registry with a legacy-upgrade proof instead of ~90 `ALTER … except: pass`; daily online
backups exist; 3,384 lines of dead per-engine clones are deleted and a gate keeps them
gone; the dashboard binds to localhost; the RCE-grade update channel is off by default;
the layer contracts hold at zero with a ratchet that only tightened. None of that is
cosmetic — every one of those was verified in code by this pass.

**But every 08-08 money-path Critical is still in the code, unchanged.** `git diff
60ccddb..HEAD` touches zero money-path files. The double-fire on EA-ack timeout, the
timeout-means-didn't-happen re-arm, the DB close recorded when the broker close failed,
the missing `record_close` idempotency guard, the `max_open_trades` race, and halts
defaulting OFF — all NOT FIXED. This was a *conscious, documented* quarantine (stage 3,
Simon-gated), and the packs say so accurately. That honesty is to the project's credit —
but the consequence must be said plainly: **the system is no safer against losing money
today than it was on 2026-08-08**, and any narrative suggesting otherwise is ahead of
the code.

The refactor's one systematic weakness: remediation has been **instance-based, not
pattern-based**. The named offender gets fixed while a greppable twin keeps running —
`news_calendar` moved off the event loop but `news_filter.py:58` still blocks it; the
dashboard moved to loopback but the licence-activation screen still binds `0.0.0.0`;
`database.py` was split but the re-export hub and stale ratchet headroom remain.

---

## New Criticals found today (all introduced or exposed by the remediation itself)

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| C1 | **Debug mode promises safety it doesn't deliver.** The banner says "no real orders", but `_make_bridge` (runtime.py:170-179) has no debug branch: on a machine with MT5 + `bridge_credentials.json`, `FOREX_DEBUG_MODE=1` logs into the **real account** and every order path fires real orders — against a fresh debug DB with all halts default-OFF. | risk C-NEW-1 | Do not run debug mode on any machine holding MT5 credentials until the seam is wired **or boot refuses a real bridge in debug mode**. The refuse-real-bridge guard is not the Simon-gated seam edit and should land now. |
| C2 | **The new login locks Simon out of the real app.** `set_password` has no caller in real mode and the `debug/debug` seed is prod-disabled, so `verify()` rejects everything. The gate is "secure" only by being unusable. | security N1 | An afternoon fix (password-set flow) that must land before handover. |
| C3 | **CI has never gone green and structurally cannot.** `checks.yml` installs only `requirements.txt`, which lacks pytest/pytest-cov/pytest-asyncio; all 3 runs to date fail in ~2m20s with "No module named pytest" — the suite and coverage ratchet never run. | testing H1 | Enforcement is still 100% local-voluntary. Fix is three deps in the workflow + an assertion in `test_ci_workflow.py`. |

## High — fix soon, no sign-off needed

- **Activation screen on `0.0.0.0:8888`, unauthenticated** (guard.py:300), and it hosts
  the button that starts the update client — a regression from the loopback work
  (security N2).
- **`news_filter.py:58` inline `urlopen(timeout=8)`** on the async live cycles of two
  engines, failure not cached — the exact disease `news_calendar` was cured of
  (backend High).
- **No pre-migrate backup** (snapshot runs *after* migrations, despite pack 050's
  promise) and **zero restore documentation** (data).
- **FK-ordered deletes still wrong** in retention prune and `reset_simulation_data`
  (trade_repo.py:341-342) — latent only because retention is default-off (data H1).
- **Licence HMAC secret still `CHANGEME-BEFORE-PRODUCTION`** (keygen.py:17);
  `CERT_NONE` still in both `remote/tls.py` and `sync/tls_util.py` — latent
  (single-node), but the docstring promises pinning that doesn't exist.
- **Stale ratchet baselines**: `structure_baseline.json` still lists database.py at
  1,251 (actual 456) and names deleted files — ~800 lines of silent regrowth headroom.
  Re-tighten after every win.

## The Simon session (stage 3) — unchanged and still the whole ballgame

In recommended order (risk + data passes agree):

1. `record_close` idempotency / `AND status='open'` guard — a live duplicate is already
   documented in code (ticket 1572181515); double closes double-credit the sim balance
   and double-feed the breaker.
2. Order-send dedup (broker-visible trade id; stop the EA-ack-timeout second fire).
3. Timeout/None/exception = UNKNOWN + the startup/report-only reconciliation service
   (position_sync.py already covers part of this — the 08-08 review under-credited it).
4. Never record a DB close when the broker close failed (monitor_loop.py:121-129).
5. Halts ON by default + un-swallow the breaker/governor recording excepts
   (close_trade.py:262-263 — a locked DB during a losing streak silently under-counts
   the streak, i.e. the breaker fails exactly when needed).
6. Atomic open-slot claim (open_trade.py:203-206).
7. The `_make_bridge` debug seam (3 lines) + demo session.

## Medium / scheduled

- Split `settings.py` (still 3,112 lines, MT5-bridge `subprocess.Popen` in a view) using
  the trading-package split as the template — that split was verified as real
  decomposition, not a cosmetic move, and its static wiring test caught 5 latent bugs.
- `history.py` imports runtime privates for P&L math in a view; format helpers
  copy-pasted in 4 panels + a second set in `trading/_shared.py`; 31 synchronous
  `ui.timer` polls; 40 silent excepts (now gated shrink-only — drain them).
- risk↔cluster import cycle (8 each way), cross-engine indicator borrowing, the
  ~202-line upward re-export hub in `db/database.py`.
- Raw analytics connections outside both managed DB layers (read_repo,
  ai_analysis_repo, telegram/repo, reversal_engine_repo).
- Facade gate passes vacuously if `TradingRuntime` is renamed; loc/sql/transaction
  ratchets still scan-and-pass on a vanished tree; `tools.checks coverage` alone can
  grade a stale artifact.
- Registry has no checksum against editing a shipped migration step's SQL.

---

## What is genuinely healthy now (verified, don't "fix")

- `tools.checks all` is trustworthy **locally**: every gate traced fails closed, each
  pinned by a negative-control test; probability it catches a broken close path when
  actually run: high. Baseline history is clean — one lowering ever, annotated, for a
  dead-code deletion.
- The migration registry, backfills, and legacy-DB upgrade proof are the real thing.
- The frozen close path, atomic signal claim, miss-streak=2, and manual-SL plausibility
  guard remain intact. Test-side MT5 discipline is now an executable invariant (import
  banned by gate), zero skips/xfails.
- New code is model-quality: `auth_gate.py` (minus the missing password-set flow),
  `start_here.py`, the surface-pinned `FakeMT5Bridge` with error injection, the
  seeded `components/` (6 modules).
- The docs tell the truth. PROGRESS/pack notes accurately distinguish landed from
  deferred — the failure mode this repo's history warns about (claimed-but-not-real
  work) was **not** observed in this pass, with one exception: the debug-mode banner
  (C1) promises more than the code delivers.

## Bottom line

Grade the refactor in two halves. **Engineering discipline: transformed** — from
guardrails that lied to guardrails that can't, from an unversioned schema to a real
migration system, from silent drift to ratchets and honest progress logs. **Money
safety: unchanged by design** — everything dangerous on 08-08 is dangerous today, plus
one new trap (debug mode with real credentials). The three new Criticals are all small
fixes (a boot guard, a password flow, three CI deps) and none needs Simon. Land those,
then the entire remaining risk concentrates in one place: the stage-3 Simon session.
