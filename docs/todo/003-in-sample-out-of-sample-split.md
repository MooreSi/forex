# 003 — In-sample / out-of-sample split for the template backtest

**Status:** **SHIPPED 2026-09-15** — phases 1 and 2 both built, `tools.checks all` green (11/11) after each. The split is on the Backtest page, **off by default** (`In-sample split (%)` = 0). One open owner decision: handover 036, the minimum trades per side.
**Domain:** analytics (`docs/system/domains/analytics/README.md`)
**Touches money:** no order path is touched. The backtest places nothing and
reaches no broker. But its comparison table is how a template gets chosen to
trade real money, so a wrong number here spends money one step later.
**Related:** `docs/todo/backtest/010-ea-templates-and-ticks.md` (the tick walk
this must not disturb), `docs/simon-handover/036-how-few-trades-is-too-few.md`
(the one open decision).

## 1. What is wrong today

The template backtest reports one number per strategy, computed over the whole
loaded window. There is no split: `grep -niE "split|purge|embargo|holdout"
backend/src/services/backtest/` returns one docstring and nothing else.

That matters because the constants those numbers validate were chosen by
looking at the same window. `engine.py:33-39` carries `_GDVR_SL_MULT = 4.0`,
`_GDVR_SL_CAP_PT = 20.0`, `_GDVR_SL_FLOOR_PT = 8.0`, annotated:

> Validated against 259 Gold Diggers VIP signals (May-Jun 2026): baseline
> (stated SL, full close @ TP1) averages -0.127R/trade; this ladder averages
> +0.167R/trade at 88.7% win rate

`+0.167R` was measured on the signals that picked the multiplier. Part of that
figure is the strategy and part of it is the choosing, and the report cannot
tell you which part is which. The same applies to every `_GDVR_PCTS` /
`_CLIMBER_PCTS` ladder shape and to `_TRAIL_DIST_PTS`.

The rest of the system already knows this. `reversal_engine/meta_label.py`
refuses to arm a model that cannot beat a coin out of sample and purges its
folds; `reversal_engine/pro_model.py:222` uses out-of-fold AUC explicitly
because "with a few hundred rows an in-sample" number is worthless. The
template backtest is the one place that skipped the lesson, and it is the place
that decides which template runs.

## 2. What changes

A run optionally partitions its signals by creation time into two independent
accounts and reports both, side by side, with the out-of-sample side named as
the one to believe.

**Phase 1 — engine and controller. No UI.**

New module `backend/src/services/backtest/split.py`. It is a new module, not an
addition to `engine.py`, because `engine.py` is at 748 of the 800-line ceiling
and is not in `structure_baseline.json`, so it cannot be raised. It is imported
by `engine.py` in the same change, so it needs no `orphan_module_allowlist`
entry.

It holds:

```python
@dataclass
class SplitStats:
    boundary_ts:      float            # unix epoch UTC; first OOS signal
    requested_frac:   float            # what was asked for
    achieved_frac:    float            # what the tie rule actually gave
    in_sample:        Optional[StrategyStats]
    out_of_sample:    Optional[StrategyStats]
    in_sample_note:   str = ""         # why there is no number, when there isn't
    out_of_sample_note: str = ""

def partition(signals, fraction) -> tuple[list, list, float]
```

`StrategyStats` gains one field, `split: Optional[SplitStats] = None`. Every
existing caller and every existing test is unaffected by a defaulted field.

`run_backtest()` gains `split_fraction: float = 0.0`. Zero means no split and
the function behaves exactly as it does today. Non-zero partitions the signals
and runs the walk **three times**: once combined (unchanged, still the headline
row) and once per side.

**Each side runs as an independent account from the same `starting_balance`.**
This is a deliberate choice and the reason is comparability: `run_backtest`
recomputes lot size on current equity after every trade, so a side continued
from the other side's closing balance would have its dollar P&L scaled by how
the first half went. A good in-sample half would inflate out-of-sample lots and
therefore out-of-sample dollars, which is the exact contamination this spec
exists to remove. It matches the guarantee already in `run_backtest`'s
docstring: "Each strategy gets an independent account; results are not
cross-contaminated."

**Partitioning is by `created_ts`, sorted, never by list position.**
`repo.fetch_backtest_signals` orders by `created_at`, but manual signals do not,
and relying on incoming order is how this silently stops splitting by time.

**Tied timestamps never straddle the boundary.** The index implied by
`fraction` is walked forward until the timestamp changes, so no two signals
sharing a creation time land on opposite sides. `achieved_frac` reports where
it actually landed, because the requested fraction is a request.

**A side too thin to mean anything gets a note, not a number.** Below the
minimum trade count the side's `StrategyStats` is `None` and the note says why.
This follows the precedent already recorded in the analytics domain file: a row
of zeros beside a row showing real drawdown reads as an argument for the
strategy that was never measured. The minimum is a judgment about when a number
is believable, so it is an owner decision — provisional default **20 trades per
side**, recorded in `docs/simon-handover/036-how-few-trades-is-too-few.md`.

`backtest_controller.py` forwards the new kwarg. It is 44 lines against a
200-line controller ceiling, so there is room; it stays a flat forward with no
logic, per the controller rule.

**Phase 2 — the page.** `frontend/pages/backtest.py` is 771 of 800 lines and
already has two `_render_*` functions against a limit of three. Adding a
fraction input, threading it through `_run_backtest`, and rendering a split
summary will not fit. So phase 2 **starts** by converting `pages/backtest.py`
into a `pages/backtest/` package per `/split-file` and §2-3 of
`/frontend-conventions` (`__init__.py` composing, `_results.py` taking the
existing `_render_results`, `_split.py` taking the new section), and only then
adds the UI. The summary states the boundary date, the per-side signal counts,
the achieved fraction, and the sentence naming out-of-sample as the line to
believe.

## 3. What must NOT change

- **No order path is touched at all.** Nothing in this spec imports
  `services/trading`, `services/broker` or `services/risk`. No demo session is
  needed and none is authorised by it.
- **`run_backtest()` with no split requested must be byte-identical.** Same
  dict, same keys, same field values, including `equity_curve` and
  `trade_list`. `split_fraction=0.0` is the default and the existing call in
  `frontend/pages/backtest.py:529` is unchanged in phase 1.
- **`_compute_stats` is not modified.** Both sides are computed by calling it
  on their own trade list. If per-side statistics need something it does not
  produce, that is a separate spec.
- **`_simulate`, `_simulate_template`, `_simulate_ticks`,
  `_simulate_ticks_template`, `filter_signals` and `_template_refusal` are not
  modified.** The split partitions the input to the walk; it does not change
  the walk.
- **`unsupported_reason` and the "NOT SIMULATED" badge keep their current
  behaviour**, and `tests/backtest/test_unsupported_template_reason.py` must
  pass unmodified. A refused template is refused on both sides, and the
  refusal, not a split, is what the row shows.
- **`_BROKER_TZ_OFFSET` handling is untouched.** The split reads
  `BtSignal.created_ts`, which is already true UTC, and never reads a candle
  timestamp. It must not acquire an offset correction of its own.
- **Every test under `tests/backtest/` passes unmodified.**
- **The combined row stays the headline row.** The split is added beside it,
  not in place of it. Removing the combined number would break continuity with
  every figure previously recorded in `engine.py`'s comments.

## 4. Non-goals

- **Does not re-tune anything.** `_GDVR_SL_MULT`, the ladders and
  `_TRAIL_DIST_PTS` keep their current values. This spec builds the instrument
  that measures them; deciding what to do about what it reads is separate work
  and a separate owner decision.
- **Does not add purging or embargo.** `meta_label.py` needs them because
  overlapping label windows leak across a fold boundary. Here each signal is
  one trade with one entry time, and the walk already refuses to look before
  a signal's creation timestamp. A gap between the two sides can be added later
  if a hold-time overlap turns out to matter; it is not assumed now.
- **Does not split the tick walk.** `run_backtest_ticks` is unchanged in phase
  1. Tick windows are short because tick data is heavy, so a split usually
  leaves both sides under any believable minimum. `partition()` takes only
  signals and a fraction, so it is walk-agnostic by construction and wiring it
  to the tick walk later is one line.
- **Does not add walk-forward, rolling windows, or multiple folds.** One cut,
  two sides.
- **Does not change how lot size is calculated**, how commission is charged, or
  how `max_drawdown_pct` / `sharpe` / `profit_factor` are defined.
- **Does not persist split results.** Nothing is written to any DB.

## 5. Test plan

Written before the code, in `tests/backtest/test_split.py` unless noted.

| # | Assertion | How I know the test can fail |
|---|---|---|
| 1 | `partition()` splits by `created_ts`, not list position: a shuffled input yields the identical partition to the sorted one | Shuffle a fixture whose creation order differs from list order. A slicing implementation returns a different partition and the test goes red. Confirm by writing the slicing version first and watching it fail. |
| 2 | `run_backtest(split_fraction=0.0)` is field-for-field equal to `run_backtest()` on the same input | Same test asserts a non-zero fraction produces a populated `split`, so the fixture is capable of distinguishing the two paths. A test that only checked equality would pass against a `split_fraction` that was ignored entirely. |
| 3 | Each side starts from `starting_balance`: `oos.equity_curve[0] == starting_balance` and `oos` lot sizes equal a standalone `run_backtest` over the OOS signals alone | Fixture's in-sample half is strongly profitable, so a continued-balance implementation gives visibly larger OOS lots. Assert the lot equality, not just the first equity point, or a continued balance with round-to-min lots could slip through. |
| 4 | Signal-id sets: `in_sample ∪ out_of_sample` equals the combined run's filled signal ids, and the intersection is empty | Not simply `len(is) + len(oos) == len(combined)` — that holds for an off-by-one that moves a signal across the boundary. The set assertion catches it; verify by moving one signal deliberately and watching it go red. |
| 5 | Tied timestamps never straddle: three signals sharing one `created_ts` land wholly on one side, and `achieved_frac` differs from `requested_frac` accordingly | Fixture places the tie exactly on the requested index. A naive index cut splits the tie and fails. Assert `achieved_frac != requested_frac` too, so a fix that silently reports the requested value is still caught. |
| 6 | A side below the minimum gets `None` stats and a non-empty note; a side at exactly the minimum gets a populated `StrategyStats` and an empty note | Parametrised at `min-1`, `min`, `min+1`. The boundary case is the one that fails if the comparison is `>` instead of `>=`. |
| 7 | `split.py` never imports from `services/trading`, `services/broker`, `services/risk`, or `backend.src.db` | Static assertion on the module's imports. Fails if a later change reaches for a live price or a real lot-size helper. |
| 8 | Phase 2 only: the rendered summary contains the boundary date, both signal counts, and the out-of-sample label | Assert on the composed text. Negative control: a run with no split renders none of it. |

Existing suites that must stay green unmodified:
`tests/backtest/test_unsupported_template_reason.py`,
`test_template_dispatch.py`, `test_tick_dispatch.py`,
`test_template_simulator.py`, `test_template_simulator_atr.py`.

## 6. How we will know it worked

Run the split against the 259 Gold Diggers VIP signals from May-Jun 2026 that
produced the `+0.167R` figure, at the default fraction, and read the two
numbers.

It has worked if the two sides are reported separately with their boundary and
counts, whatever they say. The result is not a pass/fail criterion — an
out-of-sample figure well below `+0.167R` is the instrument working, not the
instrument broken, and is precisely the thing worth knowing before the next
tuning session.

What it produces goes back into `docs/system/domains/analytics/README.md` and
into the comment block at `engine.py:33-39`, which currently states a single
number with no indication of which window chose it.

## 7. Build log — phase 1

Shipped: `backend/src/services/backtest/split.py` (131 lines, new),
`engine.py` +21 lines (748 → 769), `backtest_controller.py` +7 (44 → 51),
`tests/backtest/test_split.py` (14 tests, new).

**Two deviations from sections 2 and 5, both deliberate:**

- `run_backtest`'s `split_min_trades` defaults to **0, meaning "use
  `split.MIN_TRADES_PER_SIDE`"**, rather than defaulting to 20 directly. A
  literal 20 in `engine.py` would be a second copy of a number the owner is
  expected to change, and the two would drift the first time it moved.
- Section 5 listed eight tests; there are fourteen. The extra six are the
  capability controls written as their own named tests rather than as
  assertions buried in the test they guard (`test_the_fixture_can_tell_the_two_paths_apart`),
  plus `test_a_refused_template_gets_no_split`, which section 3 required but
  section 5 had no row for.

**One fixture defect, found by the tests and fixed in the fixture, not in an
assertion.** The helper sized its candle series to the length of the signal
list, so the standalone out-of-sample run in test 3 walked a *shorter* series
than the split run and its signals fell outside it. The comparison would have
been between two runs of different data. Every run now walks the same fixed
24-cycle series.

**Mutation-checked, five mutants, all killed by the intended test:**

| mutant | killed by |
|---|---|
| `partition` uses list order instead of `created_ts` | `test_partition_sorts_by_created_ts_not_list_order` |
| the tie walk removed | `test_tied_timestamps_never_straddle_the_boundary` |
| thin-side threshold `>` instead of `>=` | `test_a_thin_side_is_noted_not_numbered[6-True]` |
| a refused template gets split anyway | `test_a_refused_template_gets_no_split` |
| a side sized off a different balance | `test_each_side_starts_from_the_same_balance` **and** `test_out_of_sample_lots_match_a_standalone_run_of_those_signals` |

`__pycache__` was purged between every mutation and every restore.

## 8. Build log — phase 2

Shipped: `frontend/pages/backtest.py` → `frontend/pages/backtest/` (package),
`_results.py` (249 lines, the comparison table and trade logs moved verbatim),
`_split.py` (100 lines, new), `__init__.py` 771 → 562.
`tests/frontend/test_backtest_split_section.py` (8 tests, new), two landmarks
added to `tests/frontend/test_remaining_pages_render.py`.

**The page had no tests, so writing them was the first task.** `/split-file`
refuses a split of an untested file, and `frontend/pages/backtest.py` had
nothing — no test in the tree imported it or named it except two source-text
greps. Two landmarks went into `test_remaining_pages_render.py` first, and
both were validated the way that file's docstring demands: `render()` was
stubbed to return immediately and both went red, then green on restore. That
file exists for exactly this ("Written BEFORE any of these files were split").

**The undefined-names gate earned its place.** Extracting the results section
by line range cut `_fmt_pf` in half: its final `return f"{v:.2f}"` stayed
behind as a stray statement at module scope. Both modules imported, the page
rendered, and **136 tests passed**. The gate reported `undefined name 'v'`
immediately. Recorded in the frontend domain file; same family as
`docs/todo/bugs/018`.

**Two source-text greps had to be repointed, and widened while repointing.**
`test_template_dispatch.py` and `test_tick_dispatch.py` read the page as text
from a hardcoded path. Pointing them at `backtest/__init__.py` would have made
`assert "_STRATEGY_LABELS" not in code` pass vacuously as soon as that code
moved into a section module, so both now read every `*.py` in the package and
assert the directory is non-empty first.

**The split table's decision is a pure function.** `_split.side_row()` returns
either five cells or the note, and the widget code renders whichever it is
handed. That is what the tests cover; the widget code itself is exercised by a
scratch probe that built all three shapes (both sides measured, one thin, both
thin) without erroring. Mutation-checked, three mutants, all killed:

| mutant | killed by |
|---|---|
| a thin side returns zeroed cells | `test_a_side_with_no_stats_returns_its_note`, `test_it_is_not_a_row_of_cells` |
| the broker offset applied to the boundary | both tests in `TestTheBoundaryIsLabelledInUTC` |
| infinite profit factor falls through to `str()` | `test_infinite_renders_as_a_symbol` |

**Deliberately left off:** the split is **off by default** (input value 0), so
nothing about an existing run changes until it is switched on. Turning it on
by default would change what every run does and triples the walks; that is the
owner's call, not a side effect of building the control. `__init__.py` is 562
lines and still holds `render()` as one 440-line closure — frontend-conventions
wants `__init__.py` to compose rather than implement, and it does not yet.
Decomposing that closure is a separate job with its own tests, and
`/split-file` is explicit that a split must not carry a behaviour change.

## 9. Verification checklist

- [x] `python -m tools.checks all` green: 11/11 after phase 1 (suite 412.7s) and again after phase 2 (406.4s)
- [x] Every test in section 5 written first and observed red (ImportError on `split`) before the code existed, then mutation-checked — see section 7
- [x] `engine.py` 769/800, `backtest_controller.py` 51/200, page package 562/249/100, `structure_baseline.json` untouched
- [x] `split.py` imported by `engine.py` and `backtest_controller.py` in the same change; orphan gate green, no allowlist entry added
- [x] `python tools/check_doc_links.py` clean
- [x] Analytics domain README updated: the contaminated-balance trap, why a positional slice looks correct on DB-sourced runs, and refusal vs thin side
- [x] **No real or demo order was placed, closed or modified. No broker connection was opened.** Nothing in this change imports `services/trading`, `services/broker`, `services/risk` or `backend.src.db`, and `test_split_module_imports_nothing_that_can_trade` asserts it statically.

- [x] Phase 2: the page. Built — see section 8.
- [ ] Owner decision on handover 036 (minimum trades per side), and whether the split should default to on.
