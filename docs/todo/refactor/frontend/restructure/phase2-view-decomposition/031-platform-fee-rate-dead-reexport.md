# 031 — Unpick the `_platform_fee_rate` dead re-export chain

**Status:** not started
**Touches money:** no — it is an import nobody calls. But it sits in `runtime.py`, so read
`docs/system/rules/30-architecture.md` before moving anything there.
**Layer:** backend / frontend
**Size:** small, but it needs a decision rather than a deletion

## The chain

```
mt5_performance.py       defines _platform_fee_rate
runtime.py:68            imports it and never calls it
history/__init__.py      imports it from runtime and never calls it
```

Nothing else imports `_platform_fee_rate` from `runtime`. The proper path already exists:
`backend/src/services/broker/fees.py` reaches `mt5_performance._platform_fee_rate` directly,
and its own docstring notes the page used to get there through a longer route.

## Why it is still there

`tests/refactor/test_runtime_has_no_dead_imports.py` treats an external
`from backend.src.runtime import X` as the thing that justifies runtime importing `X`. So:

- Drop it from `history/` alone → runtime's import becomes dead and
  `test_runtime_imports_nothing_it_does_not_use` fails.
- Drop it from both → `test_the_reexport_scan_finds_the_known_reexports` fails, because that
  test names `_platform_fee_rate` in its control list.

That second test is a negative control, and it exists for a good reason: three names were once
deleted from `runtime.py` as unused, and a module importing them from runtime broke at import
time. Editing its list to get green is exactly the move the control was written to catch, so
the history split left the chain alone rather than expanding into it.

## What to do

1. Confirm nothing calls `_platform_fee_rate` through either hop — `fees.py` is the live path.
2. Remove the import from `frontend/pages/history/__init__.py` and from `runtime.py:68`.
3. Then, and only then, update the control list in
   `test_the_reexport_scan_finds_the_known_reexports` — deliberately, in the same commit,
   with the reason in the message. It still guards `_apply_fee` and `_tp_level_from_extreme`,
   so it keeps working as a control.
4. `python -m tools.checks all`.

## Watch out

`_reexported_names()` matches with `from\s+backend\.src\.runtime\s+import\s+([^\n(]+)` and does
not strip trailing comments, so `from backend.src.runtime import X  # noqa` registers the name
as `X  # noqa` and the scan silently stops seeing it. Worth fixing in the same pass; it is a
scanner that can quietly under-report.
