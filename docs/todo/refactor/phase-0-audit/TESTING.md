# Running the tests

## Quick start

```bash
python3 -m pytest tests/ -q
```

That is all — the deterministic clock is on by default via `pyproject.toml`. In a
Claude Code web session the dependencies install themselves via
`.claude/hooks/session-start.sh`; locally, run that script once.

## Why this needed setting up

A fresh container reported ~84 collection errors and, once those were resolved,
159 failures. None of it was broken code. There were three distinct causes.

### 1. The suite reads the wall clock

`dpm_engine.detect_session()` branches on `datetime.now(timezone.utc).hour`, and
`is_weekly_market_closed()` returns True from Friday 21:00 UTC to Sunday 22:00
UTC. Every session-gated test therefore passes on a Tuesday afternoon and fails
on a Saturday night, with no code change in between.

That was **120 of the 159 failures**. This work happened on a Saturday; the
historical "1624 passing" baseline was recorded on Tuesday 2026-07-21.

`tools/testing/fixed_clock.py` pins both readers to a fixed market-open instant
(default Tuesday 14:00 UTC, inside the London/NY overlap so every session button
is satisfied). It patches those two functions rather than freezing `datetime`
globally, because several tests genuinely need timestamps and TTLs to advance.

```bash
python3 -m pytest tests/ --market-clock=2026-07-21T09:00:00Z   # a different session
```

This is a measurement instrument, not a fix. The underlying problem is that
production code reads the clock through a module-level global rather than an
injected dependency — worth addressing when `dpm/` is migrated.

### 2. `pytest-asyncio` was missing

Without it, every `@pytest.mark.asyncio` test **fails** rather than skipping.
That read as 26 broken tests instead of one absent package — `test_limit_order_signal.py`
(19) and `test_mt5_bridge_client.py` (7). Both files pass fully once it is installed.

### 3. Several dependencies are absent, and one is broken

The image ships a Debian `cryptography` whose `_cffi_backend` is missing, which
surfaces as `pyo3_runtime.PanicException` from unrelated tests. The hook forces a
pip-managed `cffi` over the top (`--ignore-installed`, because the Debian package
has no RECORD file and cannot be uninstalled).

Two packages are deliberately not required:

- **`MetaTrader5`** — Windows-only by design. Every import of it in this repo is
  function-local, so no test reaches one.
- **`telethon`** — its `pyaes` dependency has no wheel and its sdist fails to
  build on Python 3.11. Only the live Telegram client needs it. The hook attempts
  it and carries on if it fails.

## Known problem: the suite is flaky

**This is unresolved and it matters.** With the clock pinned and all dependencies
installed, repeated runs of *identical code* produced:

```
20, 32, 33, 39, 40, 41, 58 failures
```

The failures cluster in `tests/core/test_scan_messages_*`, and those files
**pass 53/53 when run on their own**. So state is leaking between tests; the
production code is not at fault.

One plausible cause was investigated and rejected: 40 `fresh_db` variants never
reset `db._rs_cache`/`_rs_cache_ts` on teardown, unlike the canonical fixture, so
a populated risk-settings cache can outlive its temp database. Patching the 32 of
those that genuinely use `core.database` did not change the failure count — and
with 38-failure run-to-run variance, one comparison proves nothing either way. The
patch was reverted rather than shipped unproven.

**Until this is fixed, the suite cannot prove a regression.** A change that breaks
20 tests is indistinguishable from a quiet afternoon. Fixing it is not a detour:
the leaking state is almost certainly module-level globals in `database.py`, which
is exactly what Phase 1 relocates.

See QUESTIONS.md Q1.

## Auditing tools

These are separate from the test suite and always deterministic:

```bash
python3 tools/refactor_audit/orphan_detector.py --check
python3 -m tools.refactor_audit.delegation_checker --check
python3 -m tools.refactor_audit.structure_gates --check
python3 -m tools.refactor_audit.twin_compare --diff
python3 -m tools.refactor_audit.divergence_detector
```

The last two read git history and need a full clone. On a shallow clone they
silently find nothing, which is the same false-green this audit exists to catch —
the hook runs `git fetch --unshallow`, and `tests/refactor/` skips loudly rather
than passing vacuously.
