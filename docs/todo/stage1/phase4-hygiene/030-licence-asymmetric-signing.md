# 030 — Licence: rotate the shipped secret, sign asymmetrically

**Status:** not started
**Depends on:** none
**Touches money:** no
**Layer:** service
**Leverage:** Python stdlib / existing crypto dependency only — no new runtime dep without asking
(house rule)

## Problem

Review security H4: the licence HMAC secret is hardcoded and shipped (`keygen.py:17` — still
literally `...CHANGEME-BEFORE-PRODUCTION`). Symmetric = the verifier *is* the signer, so any user
of the installed app can forge a licence for themselves or others. As distribution grows (the big
vision), this is revenue protection with a hole in it.

## Decision

Ed25519 keypair: private key stays with the owner (never in the repo, never in the installer);
the app ships only the public key and verifies signatures. Existing issued licences are re-signed
and re-issued during a grace window in which both schemes verify (old-HMAC acceptance logged and
time-boxed), then HMAC verification is deleted. Check whether an existing dependency provides
Ed25519 (`cryptography`?) — if not, the choice of primitive routes through the no-new-deps rule
with the owner.

## What must NOT change

- Currently-valid licences keep working through the grace window — no legitimate user is locked
  out by the rotation.
- No auth/licence bypass appears at any point, including "temporarily" (house rule; the grace
  window is dual-verify, not no-verify).
- Licence *policy* (what a licence permits) — unchanged; only the envelope.

## Tests first (TDD)

- `tests/licence/test_asymmetric.py::test_valid_signature_verifies` / `::test_forged_rejected` /
  `::test_tampered_payload_rejected` — behaviour + control
- `::test_private_key_not_in_tree` — structural: repo + installer manifest contain no private key
  material (pattern scan) — structural
- `::test_grace_window_accepts_both_then_only_new` — clock-pinned boundary test — boundary
- `::test_old_hmac_rejected_after_window` — the sunset actually happens — regression

## What to do

1. Confirm primitive availability against existing deps; owner call if a dep is needed.
2. Write the tests; fail right.
3. Implement verify-side; owner generates the keypair **locally** (documented one-liner; the
   session never sees the private key); public key into config/build.
4. Re-issue tooling for existing licences (owner-run); grace-window dual verify; sunset date in
   config.
5. `python -m tools.checks all`.

## Where

- `keygen.py` (becomes owner-side tooling), the licence-check service module (locate via imports
  of the current secret), installer manifest

## Acceptance

- Forged/tampered licences rejected; a licence signed with the real private key verifies; pattern
  scan proves no private key ships; sunset test green.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- How many licences exist in the field determines the grace-window length — owner input (single
  known install today suggests: short).
