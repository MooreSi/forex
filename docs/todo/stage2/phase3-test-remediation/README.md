# Phase 3 — Test-suite remediation (trustworthy & TDD-aligned)

**Status:** not started — unblocked
**Gated on:** nothing
**Touches money:** no (tests only)

## Goal of this phase

The suite verifies rather than reassures. The 2026-08-11 test-design review confirmed the guardrails
are genuinely real now, but found a headline flaw (13 test files that assert nothing), coverage that
skips money-critical modules, and off-protocol layout + fixture sprawl. Fix those so the suite is
trustworthy and aligned with the `test-driven-development` skill.

## Evidence

[../../../reviews/2026-08-11/testing-design-review.md](../../../reviews/2026-08-11/testing-design-review.md).

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-delete-empty-stubs.md](010-delete-empty-stubs.md) | Delete the 13 gutted characterization files in tests/core (docstring/fixtures, zero `def test_`; each has a populated `_surface` twin) | no |
| [020-money-coverage-floors.md](020-money-coverage-floors.md) | Add services/broker (58.3%) + runtime.py (72.2%) to the money-critical absolute floors so they can't silently fall | no |
| [030-test-layout.md](030-test-layout.md) | Retire "closed" tests/core; add missing `__init__.py`; drop the frontend/tests ghost from testpaths; fix test_engine.py import-time env/db mutation | no |
| [040-fixture-dedup.md](040-fixture-dedup.md) | Consolidate fresh_db (115 defs) + _FakeBridge (69) onto the canonical conftest fixtures | no |

## Exit criteria

- Zero test files with a `def test_`-free body under tests/ (an AST check enforces it, with a
  negative control).
- broker + runtime.py carry absolute floors; no floor lowered.
- No duplicate test basenames without packages; testpaths has no ghost dir; test_engine.py does no
  import-time mutation.
- `python -m tools.checks all` green; exemplars to imitate noted in the review.
