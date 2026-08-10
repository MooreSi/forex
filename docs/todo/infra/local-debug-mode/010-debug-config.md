# 010 — Debug-mode config flag + DB isolation

**Status:** not started
**Depends on:** none
**Touches money:** no
**Layer:** config
**Leverage:** `config/__init__.py:74-75 _e()` env-over-yaml pattern; `db_path` derivation at `:182-186`

## Problem

There is no way to tell the app "run on fakes". No `debug`/`dev_mode` flag exists anywhere
(REVIEW.md §6), and `db_path` is keyed only by `account_env`, so a local test boot would write
into the same file names a real deployment uses.

## Decision

Add `debug_mode` (bool, default false) to `config.load()` via `_e("DEBUG_MODE"...)` following the
existing pattern — env var `FOREX_DEBUG_MODE` wins over `config.yaml`'s `debug_mode:`. Expose
`config.is_debug()`. When on, `db_path` becomes `forex_trader_debug.db` regardless of
`account_env`. (Names pending QUESTIONS.md #5 confirmation; proceed on these defaults if told
"go with recommendations".)

## What must NOT change

- A config.yaml without the new key + no env var → `load()` output identical to today
  (byte-identical dict apart from the new key being false).
- `db_path` for demo/live unchanged when debug off.
- `tests/core/test_database_init_env_switch.py` passes unmodified.

## Tests first (TDD)

- `tests/core/test_debug_config.py::test_debug_mode_defaults_false` — absent key/env → False —
  regression
- `::test_debug_mode_env_overrides_yaml` — env `FOREX_DEBUG_MODE=1` beats `debug_mode: false` —
  wiring (matches `_e()` semantics)
- `::test_debug_db_path_is_isolated` — debug on → path ends `forex_trader_debug.db`; debug off →
  unchanged demo/live names — boundary
- `::test_is_debug_helper_reflects_config` + negative control (flip the config, assert the
  helper flips — proves the test can fail)

## What to do

1. Write the tests above; run; watch them fail for the right reason.
2. Add the key in `load()` (`backend/src/config/__init__.py:81-180` block), the `is_debug()`
   helper, and the `db_path` override in the derivation at `:182-186`.
3. Add `debug_mode: false` with a comment block to `config.yaml.example` (documented fully in
   task 090).
4. `python -m tools.checks all`.

## Where

- `backend/src/config/__init__.py` — key, helper, db_path
- `config.yaml.example` — documented default

## Acceptance

- `FOREX_DEBUG_MODE=1 python -c "from backend.src import config; config.load(); print(config.is_debug())"` → True, and the resolved db_path is the debug file.
- **The killer test:** `test_debug_db_path_is_isolated` — a debug boot can never open a demo/live DB file.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

Downstream tasks read only `is_debug()` — no task re-parses env vars. Keep the flag OUT of the
DB (it must be decidable before `db.init`).
