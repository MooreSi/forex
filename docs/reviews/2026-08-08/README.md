# Full System Review — 2026-08-08

A read-only review of the whole system by six independent passes. Nothing was
run; MT5 was never touched. Each pass wrote its own report; this file is the
synthesis and the recommended order of work.

| Report | Scope |
|---|---|
| [00-review-checklist.md](00-review-checklist.md) | The questions this review was run against, and the severity bar. |
| [risk-review.md](risk-review.md) | The money path — order send, sizing, close, failure modes. |
| [backend-review.md](backend-review.md) | Architecture, layering, dead code, engines. |
| [data-review.md](data-review.md) | DB, schema/migrations, atomicity, reconciliation, sync. |
| [security-ops-review.md](security-ops-review.md) | Auth, remote/update channel, secrets, ops. |
| [frontend-review.md](frontend-review.md) | UI structure, the 001 restructure, duplication, tests. |
| [testing-review.md](testing-review.md) | Gates, ratchets, coverage shape, CI. |

---

## The one-paragraph verdict

The bones are better than the CLAUDE.md history implies: the four layer
contracts genuinely hold, controllers are thin, the frozen close path itself is
intact and witnessed by tests, MT5 fake discipline in tests is real, and there
is no unsafe deserialization or committed secret. **But the system is not
currently safe to expand**, for two independent reasons. First, several money
paths can lose money *today* — most seriously, a single signal can fire two
live orders through three different timeout/retry gaps, and a broker action and
its DB record are not written atomically with no reconciliation to repair the
gap. Second, the trading dashboard runs on `0.0.0.0:8888` with no login and the
remote-update channel is an unauthenticated code-execution path, so the account
is exposed to anyone on the same network. On top of that, two of the guardrails
that are supposed to catch regressions are silently dead — the exact failure the
project's own history warned about has already recurred. Fix the money and
access Criticals first; they are comparatively small, surgical changes. The
large structural cleanup (oversized files, the frontend restructure, dead code)
is real but secondary and can follow.

---

## Cross-cutting themes (found by more than one pass independently)

1. **"No response" is treated as "no action."** The same wrong assumption
   appears in order send (risk C2/C3), order modify (backend #2), and order
   close (risk H1, backend #3, data C1). A timeout, a `None`, or an exception
   is read as "it didn't happen," when it actually means "unknown." Every one
   of these can leave the broker and the DB disagreeing. This is the single
   most important pattern to fix, and it recurs because there is **no
   reconciliation layer** that reads broker truth and repairs local state.

2. **Protection is opt-in.** Daily-loss cap, drawdown halt, and the circuit
   breaker all default OFF (risk M1); the breaker's own recording is inside a
   swallowed except (data H6) and can be fed by a drifting sim ledger
   (backend H7). Always-on protection is effectively just `max_open_trades=1`
   and lot caps — and even `max_open_trades` is a check-then-act race across a
   broker await (data H5).

3. **Guardrails that fail open.** The orphan detector scans a deleted directory
   and passes vacuously (testing H1, backend #4); the coverage ratchet runs
   without `--cov` so it can't actually gate (testing H2); every gate does
   `if not path.exists(): continue`. Green output is again not evidence — the
   precise thing CLAUDE.md exists to prevent.

4. **"Components have no home."** The empty `components/` dir (frontend) and the
   ~2,800 lines of dead per-engine `database.py` clones + cross-engine indicator
   borrowing (backend #4, #10) are the same disease: shared code with nowhere
   to live, so it gets copy-pasted and then drifts. The 001 restructure is the
   right fix but is 0/13 started.

---

## Priority 0 — Stop the bleeding (do before ANY new feature)

These are money-loss or account-takeover risks. Most are small, targeted diffs.
Anything touching the order/close path needs a demo session per the golden
rules — I have **not** changed any of it.

| # | Fix | Evidence | Owner action |
|---|---|---|---|
| P0-1 | **Deduplicate order send.** Give every signal a broker-visible trade id (EA comment/magic) and refuse to place if one already exists; stop the EA-ack-timeout → Python-bridge fallback from firing a second order. | risk C1, C2, C3 | Demo session required |
| P0-2 | **Treat timeout/None/exception on send/modify/close as UNKNOWN, then reconcile** — never as "didn't happen." Add a startup + periodic MT5-vs-DB reconciliation that adopts/repairs orphans. | risk C2/C3/H1, backend #2/#3, data C1 | Demo session required |
| P0-3 | **Never record a DB close when the broker close failed/raised.** | backend #3 (monitor_loop.py:128), risk H1 | Demo session required |
| P0-4 | **Bind the dashboard to localhost and add authentication.** Today `0.0.0.0:8888` with no login controls a live account. | security C1 (run.py:262-277) | Do now (no money path) |
| P0-5 | **Disable or authenticate + sign the remote-update channel.** Unauthenticated ZIP-over-app RCE with `CERT_NONE`. Simplest immediate step: turn the auto-update client off until it's signed + pinned. | security C2 | Do now |
| P0-6 | **Turn protective halts ON by default** (daily loss, drawdown, circuit breaker) and fix the swallowed breaker-recording except. | risk M1, data H6 | Config + small fix |

## Priority 1 — Make the safety net real (next 1–2 sessions)

| # | Fix | Evidence |
|---|---|---|
| P1-1 | **Repair the guardrails first, so the rest of the cleanup is trustworthy:** repoint/retire the orphan detector, make every gate fail *closed* on a missing path, add `--cov` to `tools.checks`, fix the invalid `pyproject.toml` build backend + missing deps. | testing H1/H2/H3 |
| P1-2 | **Introduce a real migrations framework** with a `schema_version` table; stop running ~90 `ALTER … except: pass` on every boot; verify schema before trading. | data Critical #2 |
| P1-3 | **Make `max_open_trades` / circuit-breaker atomic** (reserve-before-await, not check-then-act). | data H5 |
| P1-4 | **Add `record_close` idempotency/status guard** (its own comment admits it's missing; 5 racy callers). | risk H5 |
| P1-5 | **Fix FK-ordered deletes** in retention/reset so a prune can't roll back wholesale; add a DB backup story (currently none). | data H3, H4 |
| P1-6 | **Configure the trading DB connection properly** (busy_timeout, WAL pragma at connect, a write lock for the two writer threads). | backend H8, data |
| P1-7 | **Move blocking `news_calendar` urllib off the event loop and cache None.** ~15s stalls on all three live engine paths. | backend #5 |
| P1-8 | **Move licence to asymmetric signing; rotate the hardcoded HMAC secret; pin the sync cert fingerprint.** | security H3/H4 |

## Priority 2 — Pay down the expansion tax (schedule; fold into the restructure)

| # | Work | Evidence |
|---|---|---|
| P2-1 | Delete the ~2,800 dead lines (per-engine `database.py` clones + orphan modules) — do this *after* P1-1 so the orphan gate can prove it stays gone. | backend #4 |
| P2-2 | Consolidate the duplicated indicators/level-detection shared across engines into one home; break the risk↔cluster and trading↔broker import cycles. | backend #10 |
| P2-3 | Start the 001 frontend restructure: answer its 4 open QUESTIONS first (already blocking), run the money-free lanes (010/030/040), then split `settings.py` (3,112 L, incl. MT5-bridge subprocess mgmt in the view) and seed `components/` with the copy-pasted format/poll helpers. | frontend 1–8 |
| P2-4 | Split `database.py` (schema vs migrations vs the 190-line re-export hub) and retire the upward re-export hub. | backend H8, data #8 |
| P2-5 | Replace 31 `except Exception: pass` UI swallows and 33 synchronous `ui.timer` polls; add the monkey-patch upgrade canary. | frontend 5/6/8 |
| P2-6 | Fill money-path coverage gaps (broker floor 58%, `mt5_native.py` and manual limit order untested) and add the absolute floors for broker/runtime. | testing M5 |

## Priority 3 — Hygiene

- Add a one-job CI running `python -m tools.checks all` so gates aren't
  voluntary (testing M4).
- Consolidate the 118 local `fresh_db` definitions; fix `tests/` layout drift
  (testing M6/M7).
- Add cluster-sync conflict detection / timestamps (data M7).

---

## What is genuinely healthy (don't "fix" these)

- The four layer contracts hold at zero violations; controllers are thin;
  `runtime.py` is a real facade.
- The frozen close path itself is intact and witnessed by tests — the risk is
  the *younger near-copies beside it*, not the path.
- Test-side MT5 discipline is solid: no test imports `MetaTrader5`, a Popen
  guard is asserted, the market clock is pinned, zero skips/xfails.
- No unsafe deserialization anywhere; no real secrets committed; Telegram
  commands gated to a single chat_id with constant-time token compare.
- Atomic signal claim and a miss-streak=2 before believing a broker close are
  good, deliberate designs.

---

## Open questions I need you to answer

These block or reshape the recommendations above:

1. **Deployment topology of :8888** — is this ever reachable beyond localhost
   (VPS, LAN, port-forwarded)? Changes P0-4 from "important" to "emergency."
2. **Is the auto-update client running continuously in the field?** Determines
   how urgent P0-5 is.
3. **Live-log contents** — `latest_logs/` was empty in this checkout; do
   production logs contain account numbers / credentials?
4. **Was the licence HMAC secret ever rotated** from the shipped
   `CHANGEME-BEFORE-PRODUCTION`, or is every install signed with it?
5. **How many nodes actually run** (single install vs the cluster)? If it's
   single-node today, all the sync/remote Criticals drop in urgency and P2-2's
   cycle-breaking gets easier.
6. **Retention** — is it enabled anywhere in the field? If off everywhere, data
   H3/H4 are latent not active.
