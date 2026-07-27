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

## The flakiness, and what actually caused it — mostly fixed

Before this was understood, repeated runs of *identical code* produced 20, 32,
33, 39, 40, 41 and 58 failures. The failures clustered in
`tests/core/test_scan_messages_*`, and those files passed 53/53 in isolation.

Bisecting for a polluting file found nothing, twice: the set of files collected
*before* the failures passed, and the set collected *after* passed too. That
ruled out ordering, which is what pointed at the real cause.

**`get_risk_settings()` caches for ten seconds, keyed on nothing but time.**

```python
_RS_CACHE_TTL = 10.0   # core_db_risk_settings.py:28
```

Every test builds its own temp database. A test that only *reads* settings
within ten seconds of a previous one silently received the previous test's
values — from a database file already deleted. `update_risk_settings()`
invalidates the cache, so tests that write were safe; tests that read were not.
That makes the suite **timing**-dependent rather than order-dependent, which is
why the count wandered, why bisection failed, and why the slower
`test_scan_messages_*` files took the brunt.

Two changes fix it:

1. **`database.init()` now invalidates the cache** (`forex_trader/core/database.py`).
   This is the real fix, and it is not test-only — see below.
2. **An autouse fixture in `tests/conftest.py`** clears the cache around every
   test, covering all 119 modules regardless of which of the 17 local `fresh_db`
   variants they define. It only clears a cache, so it cannot change what any
   test asserts — only which database answers it.

### The same bug was live in production

`cmd_switch_env` (`core_bot_commands_infra.py:196`) re-points the database at the
other environment's file via `db_module.init(...)`. It did not clear the settings
cache, so for up to ten seconds after a demo/live switch the app kept answering
with the **other environment's risk settings** — the session gates and the Max
Risk per trade % ceiling among them.

`init()` already closed stale per-thread connections, with a comment describing
an exactly analogous demo/live bug found 2026-07-21. The cache one layer up was
missed. `tests/core/test_database_init_env_switch.py` now covers it, and that
test fails without the fix.

### What is left

On an idle machine the suite goes fully green — **2022 passed, 0 failed**,
reproduced. Under CPU contention a handful of `test_scan_messages_*` tests still
flake: runs taken while other suites were running concurrently gave 14 and 41
failures, always from that same cluster.

So the range narrowed from 20–58 down to 0–14, and it is now clearly
load-sensitive rather than mysterious. Practical guidance:

- **Run the suite on its own.** Do not run two suites concurrently, which is what
  produced every non-zero result recorded here.
- **A non-zero count in `test_scan_messages_*` alone is not a regression** — re-run
  before investigating. A failure anywhere else is real.

The residual cause is still unidentified. It is not ordering: those files pass in
isolation, and pass when combined with any single other directory. It only appears
under the full suite plus load, which points at something cumulative and
time-sensitive rather than a specific polluting module. Worth finishing when
`signals/` is migrated, since that is the code involved.

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
