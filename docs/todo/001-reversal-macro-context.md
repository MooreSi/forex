# 001 — Wire market_context macro features into the Reversal Engine ML

**Status:** Building — steps 1-5 implemented 2026-09-05, awaiting the owner decision in section 3 before the first live cycle
**Domain:** engines (`docs/system/domains/engines/README.md`)
**Touches money:** no direct order path change. It *does* move the input to the
live-execution ML gate (`predicted R < 0` blocks live exec), so the gate's
decisions will change. See "What must NOT change".

## 1. What is wrong today

`backend/src/services/test_signal/market_context.py` already fetches the five
macro series that actually move gold — DXY momentum, US10Y, VIX, GVZ, TIP
momentum. Bounce consumes all five. Breakout consumes three of them
(`dxy_momentum`, `gvz_level`, `tip_momentum`, added at its `v15`).

The Reversal Engine consumes none. Its 33-feature vector is built entirely
from XAUUSD price structure, session clock, news proximity and reference-channel
behaviour. It has no view of the dollar, real yields or gold-specific
volatility — the variables that decide whether a technically clean level holds
or gets run through.

Two defects block the wiring, and both must be fixed first:

**(a) `market_context._get_hourly_closes` has no working cache.** It stores only
the last close as a packed float, so the hit branch cannot reconstruct the list
and explicitly `pass`es through to re-fetch. The comment on that line admits it.
Every `get_context()` call is therefore five synchronous yfinance HTTP round
trips, despite the module docstring promising a 15-minute cache. Breakout gets
away with it because it calls once per signal creation. The Reversal Engine
cycle is `_CYCLE_INTERVAL_S = 60`, and its candidate loop runs per direction per
level — naive wiring would put blocking network I/O inside the async engine loop
every minute, or worse, several times a minute.

**(b) `ml_engine.py` is 787 lines against `LOC_CEILING = 800`** and is not in
`tools/refactor_audit/structure_baseline.json`, so it cannot be raised. Adding
five features plus the mandatory version-history comment block will cross the
ceiling and fail the LOC gate as a *new* violation.

## 2. What changes

Five features appended to the Reversal Engine vector, `re_ml_v8` → `re_ml_v9`,
mirroring the breakout precedent exactly.

**Step 1 — repair the cache in `market_context.py` (no new behaviour).**
Cache the closes *list* under its own key with the existing `_CACHE_TTL`, and
return it on a hit. Widen the `_CACHE` value type accordingly. This is a
standalone fix that also removes four redundant fetches per breakout signal, so
it lands and is verified on its own.

**Step 2 — new module `backend/src/services/reversal_engine/re_macro.py`.**
Holds `macro_features(signal_data, ctx) -> list[float]` and
`async get_cycle_context()`, which calls `market_context.get_context()` at most
once per `_REFRESH_S = 15 min` and returns the last good context (else `{}`) on
failure. **Async and thread-offloaded via `asyncio.to_thread`**: the underlying
call is blocking HTTP and the Reversal cycle shares its event loop with position
management, so a stalled loop is not cosmetic. Step 1's cache makes the fetch
rare; this makes it non-blocking when it does happen. Reads use explicit
`is None` checks rather than breakout's `x or y or default`, which swaps a
genuine 0.0 for the default. A new module rather than
more lines in `ml_engine.py` because of constraint (b). It is imported by
`ml_engine.py` on day one, so no `orphan_module_allowlist.json` entry is needed.

**Step 3 — append to `FEATURE_NAMES`, in this order:**

| Feature | Source | Normalisation | Neutral |
|---|---|---|---|
| `dxy_momentum` | `ctx["dxy_momentum"]` | already [-1,+1] | 0.0 |
| `us10y_level` | `ctx["us10y_level"]` | `/ 6.0`, clamp [0,1] | 4.5/6.0 = 0.75 |
| `vix_level` | `ctx["vix_level"]` | `/ 40.0`, clamp [0,1] | 20/40 = 0.5 |
| `gvz_level` | `ctx["gvz_level"]` | `/ 40.0`, clamp [0,1] | 17/40 = 0.425 |
| `tip_momentum` | `ctx["tip_momentum"]` | already [-1,+1] | 0.0 |

`us10y_level` and `vix_level` are normalised here even though breakout passes
`gvz_level` raw-over-40 and skips the other two — the Reversal model runs an
SGDRegressor alongside LightGBM, and SGD is scale-sensitive. Every entry above
also goes into `_FEATURE_NEUTRAL` so the existing right-pad path back-fills the
~576 pre-v9 rows truthfully: those signals genuinely have no macro recorded.

Read precedence follows breakout: `signal_data.get(k) or ctx.get(k) or neutral`.
Values enter the frozen `ml_features_json` vector at creation, so **no schema
change** — `re_signals.ml_features_json` already stores the whole vector.

**Step 4 — both call sites, or neither.**
`reversal_engine_service.py` (~line 408) builds `feat_input`; add the five keys
there from `re_macro.get_cycle_context()`, fetched **once per cycle above the
candidate loop**, not per candidate. `reversal_engine_live_execute.py` (~line
190) rebuilds `fresh_sig` for the fill-time re-score and must get the same keys.
That file's own comment commits to "the same feature set with every dynamic
input recomputed against now"; leaving macro out there would silently make the
fill-time gate disagree with the stored vector. This is the same trap the
`rsi14` comment in that block records being caught by.

**Step 5 — version bump and discard.** `_version = "re_ml_v9"`, with the
existing discard-and-retrain-from-scratch handling. Training history survives
via `_FEATURE_NEUTRAL`; the fitted models do not.

## 3. What must NOT change

- **`extract_features` stays append-only.** The five names go on the end of
  `FEATURE_NAMES`. Nothing is inserted or reordered. The right-pad in
  `_get_training_data` is only valid under that rule.
- **A missing or failing `get_context()` must degrade to the neutrals**, never
  raise and never skip signal generation. `yfinance` is an optional import in
  `market_context.py` and stays optional.
- **No blocking network I/O added to the per-candidate path.** One context fetch
  per cycle, cached, or the engine's 60s loop stalls on five HTTP calls.
- Engine isolation: no shared DB, table, connection, ML label or parameter. The
  cross-engine *import* of `test_signal.market_context` is existing accepted
  coupling (breakout already does it at `breakout_signal_service.py:586`); this
  spec follows that precedent and does not promote the module.
- `reversal_engine.db` schema unchanged. No migration.
- The live-execution toggle, the `predicted R < 0` block, the momentum-exhaustion
  re-check and every real-order surface in `reversal_engine_live_execute.py` are
  untouched.
- Bounce and Breakout feature vectors, versions and models unchanged. Step 1
  changes only how often breakout's context call hits the network.
- Every existing test in `tests/` passes unmodified.

**Owner sign-off:** the ML gate decides whether a real order is placed. The code
change is safe, but the *first live cycle after the v9 discard runs on an
untrained model*, and the existing gate blocks live exec at `predicted R < 0`.
Confirm with Simon whether live execution stays enabled through the retrain
window or is toggled off until `_labeled_count` clears `_MIN_TRAIN = 15`.

## 4. Non-goals

- Does not change how lot size, SL, TP or the TP1–TP8 ladder are calculated.
- Does not change `_realised_r`, the label, or the `_R_LABEL_CLAMP`.
- Does not add TradingView or any new data provider. `yfinance` is already a
  pinned dependency (`requirements.txt:12`).
- Does not promote `market_context.py` out of `test_signal/`.
- Does not backfill historical macro values onto the ~576 existing rows. They
  get the documented neutrals. Backfilling would need point-in-time DXY/VIX at
  each signal's timestamp, which yfinance hourly bars cannot honestly give for
  rows older than its retention window.
- Does not split `ml_engine.py`. The new module avoids the ceiling; a split is
  separate work.
- Does not touch the backtest engine.

## 5. Test plan

Write each test first and watch it fail. Fakes only — no bridge, no network.

| # | Assertion | How it fails today (negative control) |
|---|---|---|
| 1 | `_get_hourly_closes` called twice inside the TTL performs one fetch | Patch `yf.Ticker` with a call counter; today it counts 2 |
| 2 | Second call returns the same list, not a truncated one | Today the list is refetched, so equality passes vacuously — assert on the *counter*, not the value |
| 3 | `len(FEATURE_NAMES) == 38` and the last five are the macro names in order | Fails at 33 before the change |
| 4 | `extract_features` with a full ctx returns those five values normalised as specified | Fails: vector is 33 long |
| 5 | `extract_features` with `get_context` raising returns a full-width vector ending in the five neutrals | Fails: no such elements |
| 6 | A stored 33-wide vector loaded by `_get_training_data` right-pads to 38 with exactly `_FEATURE_NEUTRAL` values | Fails: no v9 entries in `_FEATURE_NEUTRAL`, pad would be 0.0 for all five, silently mislabelling `us10y` as 0% |
| 7 | A 39-wide vector is still skipped | Guard against a future-build row; passes today, must keep passing |
| 8 | Service cycle calls `get_cycle_context()` once for N candidates | Patch and count; today N calls if wired naively |
| 9 | `fresh_sig` in live_execute carries all five keys, and its vector equals the creation-time vector when conditions are unchanged | Fails: the two paths diverge in the last five slots |
| 10 | `_version == "re_ml_v9"` and loading a v8 pickle discards the fitted model | Fails at v8 |
| 11 | Breakout and Bounce `FEATURE_NAMES` lengths and versions unchanged | Regression guard on isolation |

Test 6 is the one that matters. A pad of 0.0 for `us10y_level` tells the model
the ten-year was at zero for every historical signal — the same class of silent
label fiction that `_version` v5 was created to fix.

## 6. How we know it worked

Not "the tests are green". Green output is not evidence.

- `python -m tools.checks all` passes, including the LOC gate (confirms
  `ml_engine.py` stayed under 800 and no new orphan appeared).
- After the retrain, `get_status()["n_features"]` reads 38 and `labeled` reads
  the same trainable-row count as before the bump (the history survived).
- LightGBM feature importances after the first full retrain: report where the
  five macro features rank. **If all five land in the bottom quartile, say so
  and record it** — that is the honest outcome and it is worth knowing.

  **Correction (2026-09-05, after building it).** This criterion cannot be
  evaluated at the first retrain and was wrong to write as though it could.
  Immediately after the v9 discard every historical row is right-padded with
  the same `_FEATURE_NEUTRAL` constant, so all five macro columns have zero
  variance and LightGBM cannot split on them: the importances are zero by
  construction, before any question about gold is asked. Verified in
  `tests/reversal_engine/test_ml_v9_retrain.py`, with the control showing a
  macro column that *does* vary is picked up. The ranking only becomes
  evidence once enough signals have been created carrying real macro —
  `_MIN_TRAIN` is 15, but a fair read of five features wants far more than
  that. Until then a zero means "not measurable yet", and reporting it as
  "macro does not help" would be a false negative.
- Log a single `[RE-Macro]` line per cycle with the five values, so a wrong
  normalisation is visible in the log rather than only in a weight.

## 7. Verification checklist (fill in when shipped)

- [x] Test written first and observed failing, for each row above. The counter
      tests were red against the broken cache; the guard tests that could not be
      red first were each proved capable of failing by mutating the fix
      (TTL dropped, window ignored, wrong end of the list, `**MACRO_NEUTRAL`
      removed, live_execute re-read removed)
- [x] `python -m tools.checks all` green (11/11, exit 0, suite 355.2s), 2026-09-05
- [x] No real or demo MT5 order placed, modified or closed at any point
- [x] `docs/system/domains/engines/README.md` updated with what this taught us
- [ ] Owner decision on live execution during the retrain window recorded
- [ ] LightGBM importances for the five macro features reported — **not at the
      first retrain**, which cannot answer it (see the correction in section 6),
      but once a meaningful number of signals carry real macro values

## 8. What was actually built

- `market_context._get_hourly_closes` now caches the `_FETCH_WINDOW`-long list
  per symbol and serves any `n <= 5` from it. Bounce and Breakout inherit the
  fix; nothing about their features changed.
- `reversal_engine/re_macro.py` (new, 133 lines), imported by `ml_engine` on
  day one, so no `orphan_module_allowlist.json` entry.
- `ml_engine.py`: 33 -> 38 features, `re_ml_v8` -> `re_ml_v9`, `**MACRO_NEUTRAL`
  merged into `_FEATURE_NEUTRAL`. **The file is now 799 lines against the 800
  ceiling.** The additions were kept to nine lines for that reason and the
  rationale lives in `re_macro`'s docstring. The next change to this file needs
  a split first.
- Both call sites wired; `tests/reversal_engine/test_macro_call_sites.py` is an
  AST dataflow guard that fails if either forgets.
- `tests/reversal_engine/test_ml_v9_retrain.py` covers the round trip the other
  tests miss: a fully back-filled 33-wide history fits at 38 columns and
  `predict()` accepts a live vector afterwards. That is the path the `_version`
  bump forces on the first production cycle, and nothing else exercised it.
- No schema change, no migration, no new dependency.
