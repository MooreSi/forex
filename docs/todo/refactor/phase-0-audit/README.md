# Phase 0 — Correctness audit before restructuring

**Status:** in progress
**Domain:** refactor
**Created:** 2026-07-25

## Why this pack exists

Fifty of the fifty-one `PROGRESS.md` files under `docs/todo/refactor/` report every row
`done`, and `core-engine-wiring/PROGRESS.md` declares *"Migration COMPLETE. Every row in
README.md's tracker is 'Done'."* Some of that is not true, and the test suite cannot tell
you which parts.

The failure has a specific shape. Each extraction pack produced two test files:

- `test_X_characterization.py` — drives the method on the real `SimulationEngine`
- `test_X_surface.py` — drives the extracted function in `core_X.py`

Both pass. **Nothing asserts that the first calls the second.** So a module can be
extracted, fully tested, marked Done, and never actually wired in — while the original
inline copy keeps running in `engine.py`. Green tests are consistent with that outcome,
which is why it survived review.

This pack builds mechanical checks for that class of defect and records what they find.
No restructuring happens here. Nothing in `forex_trader/` is modified.

## What the checks are

| Check | Tool | Answers |
|---|---|---|
| 1. Orphans | `tools/refactor_audit/orphan_detector.py` | Which extracted functions does nothing call? |
| 2. Inline twins | `tools/refactor_audit/twin_compare.py` | For each orphan, is there a live copy, and do they agree? |
| 3. Divergence | `tools/refactor_audit/divergence_detector.py` | Which wired extractions silently lost statements? |

All three are AST-based. Text matching is not good enough here for two reasons the
history already demonstrates: the codebase reaches modules through aliases constantly
(`as db_module`, `as _cdb`, `as sched`, `as _et`), and the extraction produced Unicode
em-dash and arrow variants that defeated string comparison during the original work.

## Findings

### Ten orphaned functions, 456 LOC of dead code

Every one is recorded in `tools/refactor_audit/orphan_allowlist.json` with a reason, a
verdict, and the phase that resolves it. An allowlist entry is a debt record, not an
approval — the work is proved by the entry disappearing.

| LOC | Function | Verdict vs live copy |
|---|---|---|
| 276 | `core_mt5_position_sync::sync_closed_mt5_positions` | diverged |
| 62 | `core_profit_sync::close_full_after_tps` | diverged |
| 47 | `core_bot_commands_trading::cmd_close` | diverged |
| 25 | `core_fees_sizing::calculate_fees` | **identical** |
| 14 | `core_bot_commands_trading::cmd_market_price_buy` | diverged |
| 14 | `core_bot_commands_trading::cmd_market_price_sell` | diverged |
| 10 | `core_tp_trigger_tracking::check_sl` | duplicate extraction |
| 4 | `core_logic_keywords::set_all_lexicons` | no twin (harmless) |
| 2 | `core_logic_keywords::default_lexicon` | no twin (harmless) |
| 2 | `core_strategy_params::default_params` | no twin (harmless) |

Three of these are undocumented anywhere in the existing packs: `close_full_after_tps`,
`calculate_fees`, and the duplicated `check_sl`.

### The five order-path orphans share one root cause

Not five independent bugs. Every diverged copy on the order path constructs a **partial
`CloseTradeContext`** — `CloseTradeContext(bridge)` or
`CloseTradeContext(bridge, starting_balance=...)` — where the live path goes through
`engine.py:534 _make_close_trade_ctx()`, which supplies eight collaborators:

```
bridge, starting_balance, tp_cache, scale_out_last_fail,
tp_safety_net_last_alert, on_profit, schedule_profit_sync,
background_close_commentary
```

Wiring any of them as-is would silently drop up to six of those. That is why they were
deferred — and it is now detected mechanically instead of remembered. It is also the
single dependency that gates the whole trading phase.

### `core_mt5_position_sync` is the one to fix first

312 LOC, imported by nothing but its own test, while `engine.py:1346` runs the full
273-line inline copy called from `engine.py:1215`. `core-engine-wiring/README.md:65`
marks the row Done with the reasoning that it was *"resolved for free"* once
`_record_close` was wired. Wiring a callee does not wire the caller.

## Known limitations, stated plainly

- **Check 3 compares an extracted module at its add-commit against the source at that
  commit's parent.** A gap introduced by a later edit — after the file was added but
  before it was wired — falls outside that window. This is not hypothetical: the
  documented `core_handle_orb_fixed` missing `log.info` is exactly such a case, and
  Check 3 does not see it. `tests/refactor/test_divergence_detector.py` pins this
  limitation rather than hiding it.
- **Check 3's default mode filters any statement that survives somewhere at HEAD.**
  Extractions routinely split one method across several modules, so comparing against
  only the matching module reported a 133-statement "truncation" in
  `core_open_trade_from_signal` whose logic had simply moved to
  `core_signal_resolution.py`. Surviving is not the same as being *reached* — that is
  Check 1's job. The two checks are complementary and neither is sufficient alone.
  `--historical` disables the filter.
- **String-literal whitespace is normalised away.** Re-indenting a method body into a
  module function rewraps multi-line SQL. A change that alters *only* runs of spaces
  inside a string is therefore invisible. No SQL or Telegram message here depends on
  that, and the alternative was a diff too noisy to be read.
- **This audit requires full git history.** The checks silently find nothing on a shallow
  clone — the same "green means fine" failure they exist to catch. The test suite skips
  with an explanatory message rather than passing vacuously.

## Reproducing

```bash
git fetch --unshallow                                    # required; see above
python3 tools/refactor_audit/orphan_detector.py          # Check 1
python3 -m tools.refactor_audit.twin_compare --diff      # Check 2
python3 -m tools.refactor_audit.divergence_detector      # Check 3
python3 -m pytest tests/refactor/ -q                     # 42 tests covering all three
```

`orphan_detector.py --check` is the CI form: exit 1 on any orphan not in the allowlist.

## Still to do in Phase 0

- [ ] Check 4 — generate ~50 `test_X_wiring.py`, one per row in
      `core-engine-wiring/README.md`: monkeypatch the extracted function with a sentinel,
      call the engine method through its public entry point, assert the sentinel fired.
      This is the check that makes "Done" mean something, and its absence is the root
      cause of everything above.
- [ ] Collapse the duplicated test fixtures into one `tests/conftest.py` (`fresh_db`) plus
      one `make_engine(**overrides)` factory. ~110 files currently poke
      `db._thread_local`, `db._db_executor` and `db._rs_cache` by hand. Merging two dicts
      into one `TPCache` once broke 12 test files at once; moving that state out of the
      god object will break far more.
- [ ] The remaining CI guardrails: LOC gate with shrink-only allowlist (22 files over 800
      today), import contracts, SQL-outside-repo gate (85 files today, report-only),
      `transaction()` gate.
- [ ] Correct the false rows: `core-engine-wiring/README.md:65` and the tracker entries
      for the deferrals, which currently read Done rather than Deferred. Also the 25
      README headers still saying `**Status:** planning (pre-implementation)` for
      finished packs — `PROGRESS.md` is authoritative today, and that is a trap.

## Test suite status in this container

`tests/refactor/` — 42 passing.

The full suite could not be used as a regression baseline here: the container lacks the
app's dependency set (`MetaTrader5` is Windows-only, and the system `cryptography` is
broken — `No module named '_cffi_backend'`). After installing `httpx`, `nicegui` and
`cffi`, the run was 1847 passed / 159 failed, against a documented historical baseline of
1624 passing with 4 known failures. That gap is not attributable here and was **not**
investigated. This pack adds only new files — `tools/` and `tests/refactor/` — and
modifies nothing under `forex_trader/`, so it cannot affect those tests. Establishing a
real baseline needs an environment with the actual dependencies, and should happen before
Phase 1 moves any code.
