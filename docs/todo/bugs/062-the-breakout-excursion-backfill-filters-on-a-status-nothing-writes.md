# 062 — The breakout excursion backfill filters on a status nothing writes

**Status: FIXED 2026-09-16, test-first**, on the owner's instruction, the
same day the feature shipped. Found by checking its filter against the live
table instead of against its tests. **Still unproven end to end** — no
breakout signal has ever been live-executed, so nothing can yet demonstrate
the corrected filter selecting a real row.

## The claim

`breakout_signal/measure_repo.py`, all three queries:

```sql
WHERE live_exec_status='executed' AND status='closed' ...
```

**No code anywhere writes `'executed'` to `bo_signals.live_exec_status`.**

The breakout engine's live-execute path writes `"success"`:

```python
# breakout_signal_live_execute.py:318
bdb.update_live_exec_result(sig_id, mt5_ticket, vantage_sig_id, "success")
```

and reads it back the same way, twice, in the closure sync:

```python
# breakout_signal_service.py:701 and :740
if status == "triggered" and sig.get("mt5_ticket") \
        and sig.get("live_exec_status") == "success":
```

Every other value that path writes is `skipped:*` or `failed:*`.

`'executed'` is the **Reversal Engine's** vocabulary
(`reversal_engine_live_execute.py:405`, `status="executed"`). The breakout
`measure_repo` was modelled on the reversal engine's and kept its sentinel.

## The evidence

Live `bo_signals`, 124 rows spanning 2026-07-22 to 2026-09-16:

| live_exec_status | status | n |
|---|---|---|
| `skipped:live_off` | closed | 123 |
| `skipped:live_off` | expired | 1 |

`SELECT ... WHERE live_exec_status='executed'` returns **0**, and would return
0 after the engine goes live as well, because the value never appears.

For contrast, `re_signals` on the same install: 842 rows at `executed`.

## What it costs

Three things, all of which look fine from the outside:

* `excursion_backfill.backfill` considers 0 rows and reports
  `"0 measured, 0 with no tick coverage, 0 unusable, 0 failed, of 0
  considered"` — a clean, green, empty summary.
* `excursion_sweep` then **marks the day done** and logs that summary at INFO,
  once a night, forever.
* `excursion_observations` — the population `market/barrier_fit.fit_barriers`
  is meant to fit on — is permanently empty, so the reach distribution this
  whole feature exists to produce never has a row in it.

The feature was shipped precisely to answer whether `tp1_mult` should move off
1.0. It cannot answer anything.

## Why the tests did not catch it

`tests/breakout_signal/test_excursion_backfill.py`'s fixture:

```python
def _executed(fresh_repo, ..., exec_status="executed"):
```

The literal is shared between the test and the query and appears nowhere else,
so the tests prove the two agree with each other, not that either agrees with
the engine. One of the same tests uses `ml_skipped` as its negative case —
also a reversal-engine value; the breakout engine writes `skipped:*`.

Twelve mutants were run against this module. None could have caught it: a
mutant changes the code, and here the code and its tests are consistent — it
is the world they both describe that is missing.

## The fix

Reader-side. Changing the **writer** to `'executed'` would orphan the two
closure-sync reads in `breakout_signal_service.py` and the 124 rows already
stored.

* `LIVE_EXEC_SUCCESS = "success"` in `breakout_signal_repo.py`, beside
  `update_live_exec_result` — the function that writes the column.
* The three `measure_repo` queries bind it as a parameter instead of spelling
  a literal.
* `excursion_backfill`'s docstring restated the filter in prose and said
  `'executed'` there too. Corrected, with the reason.

**The three production sites keeping the bare literal were deliberately not
touched**: the write in `breakout_signal_live_execute.py` and the two reads in
`breakout_signal_service.py` sit on the order path, and swapping a literal for
an identically-valued constant there is not worth a diff on that path without
a demo session. The constant's own comment names all three.

### The test correction, stated plainly

The fixture's default was `exec_status="executed"` and its negative case was
`"ml_skipped"`. **Both are reversal-engine values that `bo_signals` has never
held**, so these tests were changed — a value production never writes is not
something a test gets to keep.

* default -> `"success"`, the value the live-execute path writes;
* negative -> `"skipped:live_off"`, which 123 of the 124 live rows carry.

Both are spelled out in the test file rather than imported from
`LIVE_EXEC_SUCCESS`, on purpose. A test that imports the same constant the
query uses only proves the two agree with each other, which is precisely what
let this through twelve mutants and a full `tools.checks all`.

Two tests were added, for the two queries that had no negative case at all:

* `test_the_reversal_engines_word_for_it_does_not_count_here` — the direct
  regression.
* `test_coverage_counts_only_what_actually_executed` — `excursion_coverage`
  carried the same wrong word and nothing held it to a real one.

With the fixture corrected and the queries still saying `'executed'`, **12 of
the file's 19 tests fail**. That is the red this fix was written against.

### What is still not proven

The filter now names a value the engine writes, but no `bo_signal` has ever
carried it, so nothing here has selected a real row. Until the breakout engine
executes live, the nightly sweep's `"0 measured ... of 0 considered"` remains
correct and indistinguishable from the bug. **Do not read a green sweep as
evidence that this works.**

Same class as 060 and 059: a number (here a sentinel) computed in one place
and applied in another, with nothing connecting the two.

## Mutants

| mutant | result |
|---|---|
| `LIVE_EXEC_SUCCESS = "executed"` (the bug, restored) | KILLED, 12 tests |
| the `live_exec_status` filter dropped from `excursion_coverage` | KILLED, 2 tests |

The second is the one that matters: before this change that query had no
negative case at all, which is how it carried the wrong status word without a
single test noticing.

## One more thing, not a defect

`measure_repo.excursion_observations` has **no caller**. The reversal engine
feeds its equivalent to `barrier_fit.fit_barriers` from `research_lab.py` and
`ai_tuner.py`; nothing does that for the breakout engine yet. That is
deliberate and the shipping commit says so — the evidence base first, the
target decision after. Recorded here so it is not mistaken later for a second
instance of this bug.
