# 002 — Ideas: an isolated data-science lab for finding the secret sauce

*Follows on from [001-review.md](001-review.md). Question asked: with the two
.db files we have, can we build a testing foundation — outside the backend,
no engine required — and keep running experiments to improve the win/loss
economics? Answer: yes, and here is the plan.*

---

## 1. Short answer

Yes. The two databases contain enough to build a **standalone replay
simulator** and an **offline ML workbench**, because for every one of the
741 historical signals we have:

- the full market context at creation time (price, ATR, ADX, session, bias,
  level type/score) — every signal has its complete **ML feature vector**
  stored (`ml_features_json`, 741/741 coverage);
- the entry zone, stop, and all eight TPs;
- what actually happened (trigger time, close time, outcome, P&L,
  max TP reached, partial closes) for 614 closed signals;
- a **~1-minute price series** for the whole 9 days, recoverable from
  `re_analysis_log` (4,864 samples, median gap 60s) — coarse, but real.

Plus 1,893 raw Telegram messages, the channel's parsed signals, and the
whole-app trade ledger for cross-checking.

**And we already have our first result before writing a line of simulator
code:** the engine's stored ML score is *anti-predictive* on this sample.
Average `ml_prob` for **losers is 0.154; for winners it's 0.078** — the
model ranks bad signals *above* good ones. Whatever it learned, it learned
backwards (or the labels it trained on are poisoned by the upside-down R:R
found in 001). That alone justifies the lab.

---

## 2. The one thing we're missing — and two ways around it

Neither .db contains candle (OHLC bar) data. Precise simulation of a TP
ladder needs to know the price *path* — did price hit TP1 before the stop?
Our options, in order of preference:

1. **Export real M1 candles for 21–31 July 2026 from MT5** (the terminal
   holds months of XAUUSD M1 history; File → Export, or a 20-line script on
   any machine with the terminal — no orders involved, read-only). Drop the
   CSV into the lab's data folder. This makes simulations trustworthy.
2. **Fall back to the 60-second price series** from `re_analysis_log`
   (+ the per-signal trigger/close/partial records, which pin down the path
   at the moments that mattered). Good enough for filter experiments
   (§5, notebooks 001–005); too coarse for tick-precise ladder redesign.

Rule for every experiment: **state which price source it used.** Findings on
the 60s series are "directional"; findings on M1 candles are "testable".

---

## 3. Proposed structure — `notebooks/` at the repo root

Exactly the shape you sketched, with one twist: **plain `.py` files written
in "cell" style** (`# %%` markers). VS Code runs them interactively like a
Jupyter notebook (Run Cell, variables pane, inline plots) but they diff,
grep and re-run top-to-bottom like normal scripts. No `.ipynb` JSON blobs.

```
c:\dev\forex\notebooks\            <- SIBLING of app/, not inside it
  README.md                        <- lab rules, index of experiments
  _shared\
    data\
      forex_trader_demo.db         <- copies of the two snapshots (read-only)
      reversal_engine.db
      xauusd_m1_2026-07.csv        <- MT5 candle export, when we get it
    lib\
      loaders.py                   <- signals_df(), prices_df(), trades_df()
      sim.py                       <- the replay simulator (one honest copy)
      metrics.py                   <- expectancy, profit factor, max DD, ...
      splits.py                    <- walk-forward day splits (anti-overfit)
  001-baseline-replay\
    README.md                      <- hypothesis, method, RESULT
    run.py
    output\
  002-ml-prob-autopsy\
  003-rr-geometry-grid\
  004-hour-and-session-filter\
  005-level-type-filter\
  ...
```

Why **outside `app/`**: the app has LOC ratchets, orphan-module gates,
layer-boundary contracts and a coverage ratchet. A lab must be free to make
messes; the app must not be able to import from it (and vice versa — the lab
talks only to the .db *copies* in `_shared/data`, never to the live backend,
never to MT5). That is the isolation you asked for.

Conventions (put these in the lab README):

- One folder = one question. Numbered, never renamed, never deleted — a
  failed experiment with a written result is an asset.
- Every `README.md` has four sections: **Hypothesis / Data used / Method /
  Result** — filled in even (especially) when the answer is "no edge".
- `_shared/lib/sim.py` is the *only* simulator. Experiments configure it;
  they don't fork it. When two notebooks disagree, the bug hunt is in one
  place.
- Data files are read-only snapshots. New snapshots get dated filenames
  (`reversal_engine_2026-08-11.db`), old ones stay.
- Nothing in `notebooks/` imports from `backend/`. If we want an exact
  formula (e.g. the fill model), copy the few lines and cite the source
  file in a comment.

---

## 4. The foundation piece: an event-level replay simulator

`sim.py` replays history one signal at a time:

```
for each historical signal (from re_signals):
    apply the FILTER under test (skip signal? -> record "skipped")
    apply the GEOMETRY under test (same entry, but new SL/TP ladder?)
    walk the price series forward from creation time:
        entry zone touched?  -> filled (else expired after 2h)
        then first touch of SL vs TP1..TP8, partials, BE move
    settle P&L into a virtual balance; log everything
```

Costs modelled from day one (the demo data gives us real spread numbers in
`trade_spread_cache`): spread + commission on every fill, because 741 small
trades is exactly where costs silently eat an "edge".

**Notebook 001 exists to calibrate it**: replay the *actual* rules against
the *actual* signals and check we reproduce roughly the recorded outcomes
(614 closed signals, −$2.9k book). Until the simulator can reproduce the
past, it has no authority over the future. This is the same discipline the
backend's own backtest package documents — we're rebuilding it small,
readable, and engine-free.

---

## 5. The experiment roadmap (each = one notebook, ~an afternoon each)

Ordered so that each result feeds the next. 001-review already tells us
where the bodies are buried; these turn suspicions into numbers.

| # | Question | Why it's promising |
|---|---|---|
| **001-baseline-replay** | Can the simulator reproduce the recorded −$2.9k? | Calibration gate for everything below. |
| **002-ml-prob-autopsy** | Why is `ml_prob` *higher* for losers? Sweep thresholds: does gating on it help either direction? Retrain a fresh model on the 741 stored feature vectors with day-based walk-forward splits. | The model is currently inverted — fixing or even just *ignoring* it is free alpha. All features are already extracted and stored. |
| **003-rr-geometry-grid** | Grid-search SL/TP geometry: min R:R at *creation* (0.75, 1.0, 1.5), fewer TP levels, wider TP1, ATR-scaled stops. | 001-review's core finding: avg loss 3× avg win. The live R:R filter already rejects 0.43:1 — the generator still creates them. Needs M1 candles for full trust. |
| **004-hour-and-session-filter** | Replay with hours 12–16 and 19 UTC blocked; try per-hour expectancy learned on days 1–5, tested on days 6–9. | The by-hour losses were the clearest pattern in the data, and the feature exists in the app but was off — this measures what it's worth. |
| **005-level-type-filter** | Trade only `asia_high` + `unicorn` + `swing` levels; drop `round_5`/`round_10`/`congestion`. | The two rare level types were the only profitable ones; round numbers were 56% of signals and most of the losses. |
| **006-cost-reality** | How much of the loss is spread/commission on tiny TP1s? | 3-point targets on a ~0.3-point-spread instrument is a ~10% haircut per trade before anything happens. |
| **007-near-miss-forensics** | Join `re_near_miss` (145 rows) + correlation columns: why do we never fire before the channel — wrong direction, wrong distance, or wrong time? | This is the stated purpose of the whole engine and it's at 0%. Maybe the goal is achievable; maybe the data says stop chasing it and trade the levels on their own merits. |
| **008-channel-signals-replay** | Simulate trading the *channel's own* parsed signals (357 in `vantage_tg_signals`) under different management rules. | INSTITUTIONAL-copy was the only profitable source (+$287/40 trades). Maybe the sauce is better *management of their* signals, not prediction. |
| 009+ | Combine winners of 002–008 into one candidate config; walk-forward test; only then discuss touching the backend. | The "secret sauce" is probably a stack of three boring filters, not one clever model. |

---

## 6. Honesty rules (what keeps this science, not curve-fitting)

1. **9 days is a small sample, in one regime** — a strongly trending gold
   market that the channel traded aggressively long. A config that wins
   these 9 days may just be "buy dips in a bull run". Counter: walk-forward
   splits *within* the sample now, and keep snapshotting new .db copies
   into `_shared/data` every week or two — the dataset grows on its own,
   and every past experiment can be re-run against the longer history with
   one command.
2. **Split by day, never randomly.** Signals minutes apart share the same
   market move; random splits leak the answer into the test set.
3. **One metric suite for every experiment** (`metrics.py`): net P&L,
   expectancy per signal, profit factor, avg win/avg loss, max drawdown,
   trade count. A filter that improves P&L by deleting 95% of trades gets
   caught by the count.
4. **Record negative results in the notebook README.** "Hour filter adds
   nothing once R:R is fixed" is exactly the kind of sauce-ingredient we're
   here to find.
5. **Simulated fills flatter reality.** Keep the backend's own hard-won
   caveat in view: live, the simulated ladder P&L "bore no relation to real
   P&L" for MT5-managed trades. The lab ranks *ideas*; final proof is
   always a demo-account run through the real engine.
6. **The .db copies contain (encrypted) credential tables** — the lab never
   reads `mt5_credentials`/`telegram_config`, and `notebooks/_shared/data/`
   should be git-ignored if the lab ever becomes a repo.

---

## 7. Suggested first move

1. Create the `notebooks/` skeleton + `loaders.py` (an hour: it's mostly
   `pandas.read_sql` with epoch→datetime handling — note both DBs mix epoch
   floats and ISO strings).
2. Build `sim.py` against the 60-second price series and run
   **001-baseline-replay** to calibrate.
3. Run **002-ml-prob-autopsy** — zero simulator dependency, pure
   dataframe work, and the inverted-model finding says there's something
   real to dig out immediately.
4. In parallel: get the **M1 candle export** for 21 Jul–today from the MT5
   terminal (read-only; no Simon decision needed) so 003 onward runs on
   real candles.

None of this touches `backend/`, places orders, or needs the engine running.
When (and only when) a config survives walk-forward in the lab, promoting it
into the engine becomes a normal `/spec` piece of work with Simon sign-off
on anything money-shaped.
