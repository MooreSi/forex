# Review remediation — phase 1: stop the bleeding

**Status:** not started
**Gated on:** nothing — this phase starts first, before any new feature work anywhere
**Touches money:** YES — tasks 010, 020, 030, 040, 060

## Goal of this phase

At the end of this phase, one signal can only ever produce one live order; the DB never claims a
position is closed when the broker says it's open (and orphans on either side are found and
repaired); the protective halts are on by default; and the dashboard is unreachable from other
machines.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-order-send-dedup.md](010-order-send-dedup.md) | Trade id at the broker + dedup check before every send (SPEC-002 C1) | YES |
| [020-timeout-means-unknown.md](020-timeout-means-unknown.md) | Timeout/None/exception on send → UNKNOWN, never retry, never re-pend (SPEC-002 C2/C3) | YES |
| [030-broker-db-reconciliation.md](030-broker-db-reconciliation.md) | Startup + periodic broker↔DB reconcile service (SPEC-003) | YES |
| [040-no-db-close-on-failed-broker-close.md](040-no-db-close-on-failed-broker-close.md) | monitor_loop must never record a close the broker refused (SPEC-003) | YES |
| [050-bind-dashboard-localhost.md](050-bind-dashboard-localhost.md) | Serve :8888 on 127.0.0.1 only | no |
| [060-protective-halts-default-on.md](060-protective-halts-default-on.md) | Daily-loss / drawdown / circuit-breaker ON by default; un-swallow breaker recording | YES |

## Exit criteria

- All six tasks Done — the money tasks (010/020/030/040/060) each with owner sign-off and a demo
  session recorded in PROGRESS.md.
- Full suite + all four structural gates green (the coverage step's pre-existing unfed state is
  noted honestly, fixed in phase 2/010 — do not hack it green here).
- Demo evidence for the two killer scenarios: forced ack-timeout → exactly one demo position;
  kill-between-place-and-record → restart adopts exactly once.
