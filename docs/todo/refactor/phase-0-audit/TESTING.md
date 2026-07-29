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

## The flakiness — FIXED

Repeated runs of *identical code* once produced 20, 32, 33, 39, 40, 41 and 58
failures, always clustered in `tests/core/test_scan_messages_*`, and those files
passed in isolation. It took three separate fixes, because there were three
independent causes wearing the same costume.

### 1. Caches keyed on time, not on which database is open

`get_risk_settings()` memoised for `_RS_CACHE_TTL = 10` seconds keyed on nothing
but time. Every test builds its own temp database, so a test that only *read*
settings within ten seconds of another silently received the previous test's
values from a file already deleted.

`core_strategy_params._cache` had an identical 10-second TTL and the same defect.
Finding the same bug twice is why `database.init()` now owns a **cache
invalidator registry** (`register_cache_invalidator`) rather than clearing each
one by hand — the next such cache is a one-line registration, not a third bug.

**Both were live bugs, not test artefacts.** `cmd_switch_env`
(`core_bot_commands_infra.py:196`) re-points the database at the other
environment's file, so for up to ten seconds after a demo/live switch the app
served the other environment's risk settings *and* strategy parameters — session
gates and the Max Risk per trade % ceiling included.
`tests/core/test_database_init_env_switch.py` covers it and fails without the fix.

### 2. "Fresh" timestamps frozen at import time — the main cause

Seven test modules did this at module level:

```python
_NOW_ISO = datetime.now(timezone.utc).isoformat()
```

That is evaluated once during **collection**, before any test runs. Production
treats a signal older than `_MAX_SIGNAL_AGE_SECS` (4 minutes,
`core_scan_messages_staleness_strategy.py:30`) as stale. The full suite takes
5–6 minutes, so by the time these tests executed, their "fresh" message was
older than the threshold and the code correctly rejected it as stale. The tests
were wrong, not the code.

This explains every symptom that made it look mysterious:

| Symptom | Why |
|---|---|
| Passes in isolation | collection-to-execution gap ≈ 0s |
| Fails in the full suite | those files run last; gap exceeds 4 minutes |
| Count varies run to run | a slower machine widens the gap |
| Bisection found nothing | no single file was polluting; elapsed time was |
| Adding any one directory did not reproduce | not enough extra runtime to cross 4 minutes |

The fix is to evaluate the timestamp per call rather than at import. Each of the
seven modules now has a `_now_iso()` / `_fresh_ts()` function.

### Result

**1996 passed, 0 failed**, reproduced. No quarantine, no re-run rule, no
"failures in this cluster are expected" caveat — the suite means what it says.

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
