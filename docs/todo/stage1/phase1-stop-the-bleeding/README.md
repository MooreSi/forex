# Stage 1 — phase 1: stop the bleeding

**Status:** money-path moved to **[stage 3](../../stage3/README.md)** (2026-08-11); the localhost
bind (050) shipped here.
**Touches money:** the money tasks that were here are now in stage 3.

## What happened

This phase originally held the P0 "stop the bleeding" work — the money-loss Criticals plus the
dashboard exposure fix. On 2026-08-11 the **money-path tasks were extracted to
[stage 3](../../stage3/README.md)** (a dedicated Simon-gated stage) so the rest of the roadmap isn't
blocked on Simon. What remains here is the one non-money task, already done.

## Docs

| Doc | Contents | Money | Status |
|---|---|---|---|
| [050-bind-dashboard-localhost.md](050-bind-dashboard-localhost.md) | Serve the dashboard on 127.0.0.1 only | no | **done** (2026-08-10) |

**Moved to [stage 3](../../stage3/README.md):** order-send dedup, timeout→UNKNOWN, broker↔DB
reconciliation, no-DB-close-on-failed-broker-close, protective-halts-on. All need Simon's sign-off +
a demo session.

## Exit criteria

- 050 (localhost bind) is done. The money-path exit criteria now live in
  [stage 3](../../stage3/README.md).
