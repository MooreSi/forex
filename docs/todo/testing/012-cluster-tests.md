# 012 — Tests for cluster/remote and cluster/sync

**Status:** deferred by the owner, 2026-08-27 — "we'll do this later"
**Blocks:** the `[loc]` drift items for `cluster/remote/server.py` (1,256),
`cluster/sync/server.py` (1,085), `cluster/remote/client.py` (894) and
`cluster/sync/client.py` (867)
**Size:** 4,995 lines, zero tests

## Why it matters

`docs/system/rules/70-file-organisation.md` marks these "blocked: needs tests
first", and `/split-file` names them as the live example of its own rule: *a
split is only safe when tests can tell you it worked.*

They are also the largest untested surface in the app, and not an incidental
one — this is remote-client **token issuance** and **admin authority**: who is
allowed to connect, what licence they are granted, and who can revoke it.

## Where to start

1. `remote/server.py` first — it owns `_pending`, `_allowed_tokens` and
   `approve_registration`, which `core_bot_panel`'s Telegram approval path
   already leans on. `tests/core/test_bot_panel_actions.py` fakes that module's
   state and is a working example of the shape.
2. Cover the refusals before the happy paths, as elsewhere in this codebase: an
   expired request, a token that resolves to nothing, an approval that
   generates no licence key, a revoked client still holding a token.
3. Only then split, per `/split-file`.

## Note

Do not start this unprompted. It was deliberately deferred, it is
security-sensitive, and it is days of work.
