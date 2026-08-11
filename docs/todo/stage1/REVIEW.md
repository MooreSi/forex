# Review remediation — evidence

This pack implements the findings of the **2026-08-08 full system review**. The evidence lives
there, not here — six read-only review passes plus a synthesis with the priority argument:

| Report | What it grounds in this pack |
|---|---|
| [../../reviews/2026-08-08/README.md](../../reviews/2026-08-08/README.md) | The P0–P3 ordering this pack's phases mirror; cross-cutting themes |
| [../../reviews/2026-08-08/risk-review.md](../../reviews/2026-08-08/risk-review.md) | Phase 1 tasks 010/020/040, phase 2 040 — C1/C2/C3 double-fire paths, H1/H2 close-path near-copies, H5 record_close race, M1 opt-in halts |
| [../../reviews/2026-08-08/data-review.md](../../reviews/2026-08-08/data-review.md) | Phase 1 030, phase 2 020/030/050 — dual-write gap, except-pass migrations, check-then-act gates, FK deletes, no backups |
| [../../reviews/2026-08-08/backend-review.md](../../reviews/2026-08-08/backend-review.md) | Phase 1 040, phase 2 060, phase 3 010/020/040 — monitor_loop close recording, news-calendar blocking, ~2,800 dead lines, engine duplication, DB re-export hub |
| [../../reviews/2026-08-08/security-ops-review.md](../../reviews/2026-08-08/security-ops-review.md) | Phase 1 050, phase 2 070, phase 4 030 — 0.0.0.0 bind, update-channel RCE, licence HMAC |
| [../../reviews/2026-08-08/frontend-review.md](../../reviews/2026-08-08/frontend-review.md) | Phase 3 030/050 — restructure 0/13, exception swallows, timer polls |
| [../../reviews/2026-08-08/testing-review.md](../../reviews/2026-08-08/testing-review.md) | Phase 2 010, phase 3 060, phase 4 010/020 — vacuous orphan gate, unfed ratchet, coverage gaps, no CI |

Review method: fully read-only — the app was never run, MT5 never touched, no DB writes.
`latest_logs/` was empty in the reviewed checkout, so live-log evidence (e.g. credential leakage,
actual halt trigger frequencies) could **not** be gathered; gather it before tuning phase-1/060
thresholds if live logs exist elsewhere.

Deployment fact from the owner (2026-08-08): single install, localhost-only, no cluster nodes —
this rescoped the security Criticals (see README "Decisions locked").
