# 010 — Migrating the 95 local `fresh_db` fixtures

**Status:** analysed, not started
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
