# Review remediation — phase 2: make the safety net real

**Status:** not started
**Gated on:** phase 1 landed (all six tasks Done, money tasks demo-signed) — except 010, which may
start any time; a working gate suite makes phase 1 itself safer to land
**Touches money:** YES — tasks 030, 040

## Goal of this phase

At the end of this phase, green actually means green (every gate scans real paths and fails
closed, the coverage ratchet is fed), the database has a versioned migration story and a backup,
the risk gates can't be raced, close recording is idempotent, and the unauthenticated update
channel is off.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-guardrail-gates-fail-closed.md](010-guardrail-gates-fail-closed.md) | Repoint the vacuous orphan gate, fail closed on missing paths, feed the coverage ratchet, fix pyproject | no |
| [020-schema-migrations.md](020-schema-migrations.md) | schema_version table + ordered migrations; retire the ~90 `except: pass` ALTERs | no |
| [030-risk-gate-atomicity.md](030-risk-gate-atomicity.md) | max_open_trades / breaker: reserve-before-await, no check-then-act race | YES |
| [040-record-close-idempotency.md](040-record-close-idempotency.md) | Status guard so five racy callers can't double-record a close | YES |
| [050-db-connection-fk-backups.md](050-db-connection-fk-backups.md) | busy_timeout + WAL at connect, write lock, FK-ordered deletes, daily backup | no |
| [060-news-calendar-offload.md](060-news-calendar-offload.md) | Blocking urllib off the event loop; cache None results | no |
| [070-update-channel-disable.md](070-update-channel-disable.md) | Auto-update client off by default until signed + pinned | no |

## Exit criteria

- `python -m tools.checks all` **fully** green including the coverage step — for the first time,
  honestly.
- A planted orphan file, a planted missing-path rename, and a stale coverage file each make the
  gate suite FAIL (negative controls demonstrated, output in PROGRESS.md).
- Money tasks 030/040 demo-signed.
