# Review remediation — phase 4: hygiene

**Status:** not started
**Gated on:** phase2/010 landed (CI is only worth wiring to a gate suite that actually gates);
020/030 may start any time
**Touches money:** no

## Goal of this phase

At the end of this phase, the checks run without a human remembering them, the test tree matches
the documented protocol, licences can't be forged with a shipped secret, and what shipped in this
pack is written down for users (this phase doubles as the pack's docs phase).

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-ci-job.md](010-ci-job.md) | One CI job running `python -m tools.checks all` on every push | no |
| [020-test-layout-consolidation.md](020-test-layout-consolidation.md) | Retire tests/core "legacy" limbo, fix packages/globs, dedupe fresh_db | no |
| [030-licence-asymmetric-signing.md](030-licence-asymmetric-signing.md) | Rotate the shipped HMAC secret; sign licences asymmetrically | no |
| [040-docs-of-what-shipped.md](040-docs-of-what-shipped.md) | CHANGELOG, in-app setup text, docs/ai rule updates for everything this pack changed | no |

## Exit criteria

- A push with a planted failing test goes red in CI without local involvement.
- `python -m tools.checks all` green; 040's docs merged; pack ready for `/spec done`.
