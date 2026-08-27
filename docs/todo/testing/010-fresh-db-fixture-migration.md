# 010 — Migrating the 95 local `fresh_db` fixtures

**Status:** done for the equivalents (2026-08-27); the genuine variants remain
**Blocks:** `tests/refactor/test_fixture_dedup.py` (2 of the 3 assertions), and therefore
`python -m tools.checks all` going green
**Risk:** low per file, but it is 95 files of judgement, not a mechanical sweep

## The numbers

| | count | baseline |
|---|---|---|
| local `fresh_db` definitions | 95 | 66 |
| local `_FakeBridge` classes | 64 | 56 |

`test_baselines_are_not_slack` asserts **equality**, not `<=`, so the count has to land
exactly on the baseline — or the baseline is lowered to meet a smaller real count, which
is allowed (it may only shrink).

Byte-equivalent copies: **zero**. There are **27 distinct variants** across the 95 files:

```
512f13f3  24 files      7572e5b1   6 files      8569190a  2 files
2664c0e8  16 files      8a51754f   4 files      fd17fc34  2 files
adccf6cc  13 files      7c11dd05   4 files      bbe5eb39  2 files
                        6908a760   4 files      489f2bf7  2 files
                                                + 15 singletons
```

## Why this is not a sweep

The canonical fixture in `tests/conftest.py` is a **superset** of the common variants:

```python
reset_thread_local_connection()          # local variants: _reset_thread_local_connection()
reset_db_worker_thread_connection()      # variants 2664c0e8 / adccf6cc omit this entirely
fd, path = tempfile.mkstemp(suffix=".db")
db.init(path)
db._rs_cache = None                      # variants 512f13f3 / adccf6cc omit both
db._rs_cache_ts = 0.0
```

So migrating a file **adds** behaviour: an extra connection reset and a cache clear. Both
look harmless — the autouse `_isolate_risk_settings_cache` already nulls `_rs_cache` around
every test, making that line redundant — but "looks harmless" is the assumption this
codebase exists to distrust, and `tests/conftest.py` says so directly:

> Migration has to happen file by file with the differences actually read: the 17 variants
> are not interchangeable, and rewriting them mechanically against a suite whose baseline is
> not currently trustworthy is how you introduce a silent regression while believing you are
> tidying up.

(It says 17; the upstream merge took it to 27.)

There is a second trap. The local variants call `_reset_thread_local_connection()` — an
underscore-prefixed helper defined **in each test file**. Deleting the fixture without
checking whether that helper has other callers in the same file leaves a NameError behind,
which is the exact bug class that `frontend/pages/test_panel.py` and
`analytics/ai_analysis_repo.py` are already carrying (see `docs/todo/bugs/`).

## Suggested order

1. **512f13f3 (24 files)** — differs only by the missing `_rs_cache` reset and the helper
   name. Largest single win, and the difference is the most clearly redundant one.
2. **2664c0e8 (16)** and **adccf6cc (13)** — these omit
   `reset_db_worker_thread_connection()`. Establish first whether any test in those files
   actually uses the DB worker thread; if none does, adding the reset is inert.
3. The 15 singletons last — each is one file and probably has a reason.

After each group: full suite, and compare the failure list, not just the count. Then lower
`FRESH_DB_LOCAL_DEFS_MAX` to whatever the real count is, in the same commit, so
`test_baselines_are_not_slack` stays meaningful.

## Do not

- Rewrite all 95 in one pass. If it goes wrong the suite tells you nothing about which file.
- Delete a local `_reset_*` helper without grepping the file for its other callers.
- Raise either baseline.

---

## Done (2026-08-27)

Both ratchets pass.

    local fresh_db definitions   95 -> 66   (baseline 66, unchanged)
    _FakeBridge classes          64 -> 50   (baseline 56 -> 50, lowered to match)

**fresh_db.** The census above said zero byte-equivalent copies, and that was
wrong -- it was comparing docstrings and a `-> None` annotation. Comparing the
statements by AST: all 90 files' local `_reset_*` helpers are identical to the
conftest functions they shadow, 4 fixtures are statement-identical, and 25
differ only by the two `db._rs_cache` lines that the autouse
`_isolate_risk_settings_cache` already performs around every test. Those 29
were migrated; the other 66 are genuine variants and were not touched. 29 is
exactly the gap to the baseline, which is where 66 came from in the first
place.

**_FakeBridge.** The shared fake this ratchet anticipated now exists at
`tests/_fakes.py`. Fifteen files carried one of two identical shapes -- one
recording `modify_order`, one recording `modify_order` and `partial_close` --
and the second is a superset of the first, so one class covers both. It is
still named `_FakeBridge` so the ratchet keeps counting it: hiding a shared
fake behind a name the regex does not match would improve the number without
improving the codebase. The baseline was then lowered to the real count, which
this ratchet explicitly permits.

**What is left.** 66 fresh_db variants and 49 bridge fakes, all genuinely
different. Each needs its differences read before it can move, which is what
`tests/conftest.py` has said all along. Nothing here should be swept.

**Two mistakes worth recording.** The first comparison pass reported zero
equivalents because of docstrings, which would have made this look impossible.
The consolidation sweep then globbed `tests/**/*.py`, matched the shared fake
it had just written, deleted it and replaced it with an import of itself -- 15
collection errors, caught immediately by the suite.

