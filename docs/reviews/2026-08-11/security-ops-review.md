# Security & Operations Review — FOREX Trader (live-money MT5)

- **Date:** 2026-08-11
- **Reviewer:** Security & ops (owner-authorized, read-only, one of six)
- **Scope:** Dashboard bind + new auth gate (commit `5e942c6`), remote-update channel,
  licence system, secrets handling, Telegram gating, sync/cluster cert pinning, installer, CI,
  operational story.
- **Method:** Static read-only source review against the current tree. App never run; MT5 never
  touched; no tests/tools.checks executed.
- **Deployment reality (given):** SINGLE install, localhost-only, NO cluster, no port-forwarding,
  run by a non-developer (Simon). Severities recalibrated to that, with residual risk noted.

---

## Summary & verdict

Two of the three big things moved in the right direction. The dashboard now **defaults to
`127.0.0.1`** (`config/__init__.py:182`, `run.py:218-235`) with a loud warning on any non-loopback
bind, and the remote-update/RCE client is now **off by default** (`remote_admin_client_enabled`
default `False`, `config/__init__.py:194-196`; gated in `app.py:190-199`) and only ever starts
behind a shouted warning. Those close C1's network hole and C2's always-on exposure for the
single-localhost reality. A real login gate was also added (`frontend/auth_gate.py`) with
scrypt-hashed password storage outside the repo.

But the refactor introduced a **new, self-inflicted problem that I rate the top issue for handover:
in real (non-debug) mode there is no way to set the dashboard password, and the debug `debug/debug`
seed is disabled in prod — so the login gate is un-passable and Simon is locked out of his own live
app** (details in N1). The gate is "secure" only by being unusable. Meanwhile the **licence secret
is still the `CHANGEME-BEFORE-PRODUCTION` placeholder** (`licence/keygen.py:17`), and the
**licence-activation screen still binds `0.0.0.0:8888` with no auth gate in front of it**
(`guard.py:300`) — the one pre-login screen from which a user can also trigger the unauthenticated
update client. `CERT_NONE` remains in both remote and sync TLS, and the sync client still has no
fingerprint pinning despite the docstring promising one — but with no cluster deployed those are now
latent, not live.

**Verdict:** For a single localhost install the *network* posture is now broadly adequate — the
LAN-exposed-trading-terminal and always-on-RCE criticals are genuinely defused by the loopback
default and the update-client-off default. It is **not yet ready for handover**, for two reasons
that are both fixable in an afternoon: (1) the login gate must gain a password-set path or the app
is unusable in live mode (N1); (2) the activation screen must move off `0.0.0.0` and behind the same
gate (N2). The licence placeholder (H2, unchanged) should be rotated. Nothing here requires the
cluster/sync work the deployment reality has shelved.

---

## Previous-findings verification table

| ID | Prior finding | Status now | Evidence |
|---|---|---|---|
| **C1** | Dashboard on `0.0.0.0:8888`, no auth | **Largely fixed** for the main app. Default bind is `127.0.0.1` (`config/__init__.py:182`), resolved with a non-loopback warning (`run.py:218-235`); a real login gate now wraps all routes (`frontend/auth_gate.py:21-28`, installed unconditionally `run.py:333-334`). **Residual:** activation screen still `0.0.0.0` (see N2); login gate unusable in prod (N1). | verified |
| **C2** | Unauthenticated update-channel RCE (ZIP-over-app, `CERT_NONE`, LAN beacon) | **Mitigated by default-off, not fixed.** `remote_admin_client_enabled` defaults `False` (`config/__init__.py:194-196`); `app._remote_client_enabled` returns False unless opted in, with a loud warning when on (`app.py:180-199`). The vulnerable code path (no signature, `CERT_NONE`, beacon discovery) is unchanged — only gated. First-run activation now starts the client **only** on explicit user "Request Registration" click (`guard.py:179-202`), not automatically. | verified |
| **H1** | Sync client no cert verification / no fingerprint pin | **Unchanged.** `sync/tls_util.py:95-98` still `check_hostname=False`/`CERT_NONE`; docstring still points to a `_verify_fingerprint` in `client.py` that **does not exist** (no fingerprint/pin code in `sync/client.py`). Latent only — no cluster deployed. | verified |
| **H2** | Licence HMAC secret hardcoded placeholder | **Unchanged.** `licence/keygen.py:17` still `b"FOREX-SERVER-SECRET-CHANGEME-BEFORE-PRODUCTION"`; symmetric HMAC still generates and verifies. No move to asymmetric signing yet. | verified |
| **M1** | Admin server external-IP start gate | Out of scope this pass (admin machine only); code still present at `remote/server.py`. Not re-verified line-by-line. | not re-checked |
| **M2** | Admin password in-band, self-signed cert unpinned | **Unchanged** (systemic `CERT_NONE`, see `remote/tls.py:90-95`). Admin-side only. | verified (pattern) |
| **M3/M4** | `pip install` on update / floor-pinned deps | Unchanged; both are downstream of C2 which is now default-off. | not re-checked |
| **L3/L4/L5** | No unsafe deserialization; secrets clean; Telegram single-chat gate | Still healthy (see "genuinely healthy"). | verified |

---

## New findings (by severity)

### CRITICAL / HIGH (for handover usability + security)

**N1. The new dashboard login gate has no password-set path in real mode — the live app is
un-loginable (fail-closed to unusable), and the only way in is the debug fakes.**
`frontend/auth_gate.py:24` redirects every unauthenticated request to `/login`; the gate is
installed unconditionally for both modes (`run.py:333-334`). Login is decided by
`dashboard_auth.verify()` (`services/auth/dashboard_auth.py:44-53`):
- If a password **is** set → checks scrypt hash. Fine.
- If **no** password is set → returns `True` only when `is_debug()` **and** `debug/debug`
  (`dashboard_auth.py:47-48`).

In production `is_debug()` is `False` (`config/__init__.py:173-175`, default off), so with no
password file present **every** credential is rejected — Simon cannot log in at all. Crucially,
**nothing in the app ever sets the dashboard password**: `auth_controller.set_password` /
`dashboard_auth.set_password` exist but have **no caller** in `frontend/`, `run.py`, or any
first-run flow (grep: only controller/service/test references). The handover README tells Simon to
run the real app and "open http://localhost:8888" with no mention of a login
(`docs/simon-handover/README.md:75-84`), while debug mode documents `debug/debug`
(`README.md:66-73`). Net effect: to actually use the login he must either run **debug mode (fakes —
no live trading)** or hand-create the `dashboard_password.hash` file, which is undocumented.
**Impact:** Live app is unusable as shipped, or the operator is pushed toward debug mode / manual
file surgery. The C1 remediation is therefore only half-built.
**Recommendation:** Add a first-run "set dashboard password" screen (wire the existing
`set_password`), or a documented CLI/`Settings → Security` field; until then the gate should not be
installed in a mode where no password can be set. Ship with a clear onboarding step.

### MEDIUM

**N2. Licence-activation / error screen still binds `0.0.0.0:8888` with no auth gate.**
`config/licence/guard.py:300` runs `ui.run(host="0.0.0.0", port=8888, …)` for the activation, wrong-
machine, expired, and tamper screens. This runs **before** `main()` reaches `auth_gate.install()`
(`run.py:276-277` licence enforce happens before `run.py:334`), so the gate never protects it. Any
device on the same LAN can reach this screen during the activation window, and it exposes the
**"Request Registration" button that starts the unauthenticated remote-update client**
(`guard.py:179-202`) and a manual-activation form. It also hardcodes `0.0.0.0` and port `8888`,
ignoring the loopback default and the configured port (default `8890`, `config/__init__.py:165`).
**Impact:** Same-LAN exposure of a pre-login trading-app screen and a user-triggerable RCE channel,
transient but real; contradicts the C1 loopback fix. On a truly isolated single machine the residual
is low, but it is a straight regression from the loopback default everywhere else.
**Recommendation:** Bind the activation screen to `_resolve_bind_host(cfg)` / `127.0.0.1` and the
configured port; it needs no wider reach than the main dashboard.

**N3. Licence secret unrotated — still `CHANGEME-BEFORE-PRODUCTION` (carry-over of H2, restated
because it is a shipped-build gate).** `licence/keygen.py:17`. Anyone with a copy of the app can mint
a perpetual key for their own machine ID. Inherent to the symmetric scheme; CLAUDE.md forbids adding
a bypass, so this is reported, not "fixed." For a trusted single operator this is anti-casual-copy
only; the placeholder marker should still be rotated before any real distribution.

### LOW / INFORMATIONAL

**N4. Auth gate leaves the NiceGUI websocket path open by design.** `_OPEN_PREFIXES` includes
`/_nicegui` (`auth_gate.py:18`), which must stay open for the framework, so the middleware only gates
the initial HTTP page GETs, not websocket traffic. Because interactive NiceGUI clients are only
created after a gated page load, this is not directly exploitable, but the auth boundary is at page-
render time, not at the transport. Acceptable for localhost single-user; worth knowing before any
network bind is ever contemplated.

**N5. No brute-force / lockout on `/login`.** `_attempt` (`auth_gate.py:45-50`) has no rate limit or
lockout. scrypt (`n=2**14`) makes online guessing slow, and this is localhost single-user, so the
risk is minimal — noted for completeness.

**N6. Debug backdoor is correctly fenced (positive).** `debug/debug` is accepted **only** when
`is_debug()` is true AND no real password is set (`dashboard_auth.py:47-48`); debug mode also forces
an isolated `forex_trader_debug.db` and fakes (`config/__init__.py:173-175, 202-206`), so the debug
login can never reach a live/demo account. `FOREX_DEBUG_MODE` does not weaken the real app. No
default-credential backdoor is reachable in prod mode.

**N7. CI leaks nothing.** `.github/workflows/checks.yml` runs only `tools.checks all`, installs from
`requirements.txt`, and uploads `.coverage.json`. No secrets, no env injection, no deploy step. Clean.

---

## What is genuinely healthy

- **Loopback-by-default dashboard bind** with a per-launch warning on any non-loopback host
  (`run.py:218-235`, `config/__init__.py:177-182`) — the highest-value C1 fix, done well.
- **Update/RCE client off by default**, single testable predicate, loud warning when enabled, no
  automatic first-run start (`app.py:180-199`, `guard.py:179-202`). C2's continuous exposure is gone
  for normal use.
- **Password storage done right where it exists:** scrypt with per-write random salt, hash stored in
  `USER_DATA_DIR` never shipped, `secrets.compare_digest` verify, signed session cookie via a
  per-install `storage_secret` generated to the data dir at `0o600` (`dashboard_auth.py:28-53`,
  `run.py:238-262`).
- **Secrets handling still clean:** `config.yaml.example` empty, real secrets outside the repo /
  keychain, sync allowlist excludes MT5 creds + `anthropic_api_key`. No committed secrets beyond the
  licence placeholder.
- **Telegram gating** unchanged and sound (single `chat_id` allowlist).
- **No unsafe deserialization** anywhere on remote/sync input (all `json.loads`).
- **CI** is a faithful mirror of local checks and leaks nothing.

---

## Must-fix before handover (prioritized)

1. **(N1) Give the login gate a password-set path** (first-run screen or documented step), or the
   live app cannot be logged into. Without this, C1's fix is incomplete and the operator is pushed to
   debug/fakes.
2. **(N2) Bind the activation screen to loopback + configured port** and put it behind the same gate;
   stop it hardcoding `0.0.0.0:8888`.
3. **(N3/H2) Rotate the licence secret** off `CHANGEME-BEFORE-PRODUCTION` (accept as anti-casual-copy
   only, or move to asymmetric signing).
4. Deferred while no cluster ships: **H1** sync fingerprint pinning, **C2** signing/pinning of the
   update channel — keep them off; do the security work before ever enabling either.

---

## Open questions

1. Is Simon expected to hand-create `dashboard_password.hash`, or was a set-password UI intended and
   dropped? (N1 — this determines whether the live app is usable as shipped.)
2. Is the activation screen's `0.0.0.0` bind deliberate (to allow activation from another device) or
   an oversight left over from the pre-loopback design? (N2)
3. Has `_SERVER_SECRET` ever been rotated in any shipped/live build, and does
   `/Users/simon/Documents/KeyGen/keygen.py` still match the placeholder? (N3)
4. On the real install, which port is actually served — config defaults to `8890` but the handover
   and the licence screen both say `8888`; is a `config.yaml` overriding it?
