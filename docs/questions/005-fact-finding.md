# Q005 — Facts only the operator knows

**Decision:** PROVISIONAL — assumptions recorded per item below; work proceeds on
them. Confirm or correct each.
**Who decides:** Darren for operational facts; the brother for the licence one.
**Consumed by:** scopes several tasks (security, licence, retention, halts).

These are not design choices — they're facts about the running system that
weren't visible from the code. Each has an assumption we're proceeding under.

## 1. Do the live logs contain secrets or account data?

`latest_logs/` and `archived_logs/` were **empty** in the reviewed checkout, so
credential/PII leakage in logs could not be checked. The diagnostics uploader
also ships ~3,000 raw log lines to the admin server.
**Assumption:** logs may contain account numbers; treat as sensitive until shown
otherwise.
**Answer (do prod logs contain credentials / account numbers / PII?):**

## 2. Was the licence HMAC secret ever rotated?

`keygen.py` still ships the literal `...CHANGEME-BEFORE-PRODUCTION` secret. If it
was never rotated, every install is signed with the same shipped key (anyone can
forge a licence). This scopes the urgency of phase4/030.
**Assumption:** never rotated (worst case) — phase4/030 moves to asymmetric.
**Answer (was it rotated? how many licences exist in the field?):**

## 3. Is the auto-update client actually running in the field?

Determines how urgent the update-channel lockdown is. Single-node localhost was
confirmed, but not whether the update client runs.
**Assumption:** not actively used — phase2/070 disables it by default regardless.
**Answer (is the update/remote client running anywhere today?):**

## 4. Is data retention enabled anywhere?

Retention (prune of old trades) is opt-in, default off. If it's off everywhere,
the FK-delete and audit-trail concerns are latent, not active.
**Assumption:** off everywhere — phase2/050 fixes the FK ordering anyway.
**Answer (is retention turned on in any install?):**
