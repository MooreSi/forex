# 070 — Ship the fleet's learning to every client, without losing theirs

**Status:** **ANSWERED 2026-09-11, and the answer overturns the design below.**
Owner: *"i dont want to share trade data with other users of the app just the
learned ml engine as it develops."* So: **ship the model, not the rows** — the
opposite of what this file recommends. The original design is kept in full
because its four objections are the cost of the answer, and the revised design
at the bottom has to pay each one. **NOT BUILT.**
**Raised by the owner:** *"I want the remote clients/users to be able to
immediately take advantage of the trained data/weights and be able to update
their model when GitHub updates but also need to consider their own training so
it would need to either sit alongside this or be amalgamated."*

## What is being asked, stated back

1. A client — new, or one that has traded little — should not start from a
   blank model. It should arrive already knowing what the fleet has learned.
2. When the app updates from GitHub, the learning updates with it.
3. A client keeps training on its OWN trades, and that must not be thrown away
   or drowned out.

## The blocker on the obvious approach

Committing `reversal_engine.db` itself does not work:

- **It is 20.9 MB and rewritten constantly.** Git stores each version of a
  binary in full, so a daily commit is roughly 600 MB of history a month,
  permanently. The repo's `.git` is 41 MB today.
- **It is live, with a WAL.** `reversal_engine.db-wal` is a separate 185 KB
  file; committing the `.db` alone captures a torn snapshot.
- **It carries configuration tables**, including `telegram_config` (1 row) and
  `email_config`. `mt5_credentials` exists there too — **currently empty, which
  was checked, not assumed** — but the schema is present, so a future
  populated row would be committed by anyone following this pattern.

CLAUDE.md: *do not commit secrets, tokens or licence keys.*

## What to ship instead: the ROWS, not the weights

**Only the feature vectors and their realised-R labels.** Measured: 4,803
labelled signals carry **1,103 KB** of `ml_features_json`. Compressed, that is
a few hundred KB — a normal thing to keep in a repo, against 20.9 MB.

**Rows rather than fitted weights, for four reasons:**

1. **It is the path that already exists.** `_collect_training_data()` builds
   `(X, y)` from rows and the model refits from scratch every 5 labelled
   signals. Fleet rows slot straight in as more rows. Fitted weights do not:
   LightGBM cannot continue someone else's model, so weights would mean
   loading a third model and blending it into `predict()` alongside the batch
   and online pair.
2. **Rows survive version bumps; weights do not.** A bump discards fitted
   models by design, and `_collect_training_data` already pads narrower
   historical vectors with `_FEATURE_NEUTRAL`. Shipped rows keep working across
   a bump; shipped weights would be binned by the very next one.
3. **Rows genuinely amalgamate.** A client that retrains on fleet + own rows
   has one model that knows both. A client that loads foreign weights is
   borrowing someone else's judgement and keeping its own separately.
4. **Rows carry nothing identifying.** A feature vector and a realised R
   multiple. No ticket, no account, no channel name, no balance.

## Shape of it

**Export** (`tools/export_ml_corpus.py`, run before a push): every closed
signal with features and a realised R, written as compressed JSONL to
`data/ml_corpus/re_ml_v9.jsonl.gz`, stamped with the model version and the
feature width. Deterministic order so an unchanged corpus produces an unchanged
file and does not churn the diff.

**Import**: `_collect_training_data()` reads the corpus alongside the local
rows. Two rules that matter:

- **Provenance.** Fleet rows are tagged, so they can be weighted differently
  and — critically — **replaced wholesale on update rather than appended**, or
  every `git pull` doubles the corpus.
- **Width.** A row narrower than the current schema is padded, as today. A row
  WIDER is from a newer build and is still skipped, as today.

**Delivery needs no new infrastructure.** The app already updates itself with
`git fetch`/`git pull` (`core_app_update`), so a file in the repo arrives with
the next update.

## The decision needed — how much should a client trust the fleet?

This changes what the ML gate learns, which changes which trades are taken, so
it is the owner's call, not an implementation detail.

- **A. Equal weight.** Simplest. A client with 50 trades of its own is
  effectively trading the fleet's model, which is the point for a new client
  and possibly wrong for an established one.
- **B. Local rows weighted higher** (say 3x). The fleet is a prior; a client's
  own experience overrides it as it accumulates. Needs a multiplier chosen.
- **C. Fleet rows only until the client has N of its own**, then local only.
  Cleanest story, sharpest cliff.

**Recommended: B.** It is the only one that satisfies both halves of the
request at once — immediate benefit on day one, and a client's own market
gradually taking precedence. `_train_batch` already applies time-decay
weighting (`math.exp(-0.017 * (len(X) - i))`), so a provenance multiplier
composes with machinery that is already there.

## Not to be forgotten

The corpus is currently the record of a **losing** system: mean R is -0.083,
and items [020](020-losses-exceed-the-stop.md), [030](030-wins-are-cut-at-two-thirds-of-a-r.md)
and [040](040-filter-the-instant-fills.md) are about to change what it
contains. Shipping it fleet-wide propagates today's payoff problem to every
client. **Worth doing, worth doing after 040**, or the fleet is trained on the
version of the strategy that loses money.


---

# Revised: ship the model, not the rows (2026-09-11)

## One correction first, in case it changes the answer

The thing this file proposed sharing is **not trade data in any recognisable
sense**. A corpus row is a feature vector and one number — the realised R
multiple. **No ticket, no account number, no channel name, no balance, no
price, no timestamp of yours.** Nothing in it identifies you, your broker or
who you follow.

If the objection was to other users seeing your trades, that was not on the
table. If the objection is to sharing the raw material of your edge at all —
which is a different and perfectly good reason — the rest of this section is
the design for that.

Said once, not pressed. The design below assumes the answer stands.

## What "the learned ml engine" actually is

Two models, blended 60/40 in `predict()`:

| | what it is | can it continue from someone else's? |
|---|---|---|
| `re_ml_batch.pkl` (181 KB) | LightGBM, **refit from scratch** every 5 labelled signals | **No.** LightGBM has no partial fit |
| `re_ml_online.pkl` (1.1 KB) | `SGDRegressor`, updated by `partial_fit` per outcome | **Yes** — this is the one that genuinely can |

`re_ml_meta.pkl` stamps both with `_version` (`re_ml_v9` today) and the feature
width.

## The design

**Export.** A new `tools/export_ml_model.py` writes `re_ml_batch.pkl` and
`re_ml_meta.pkl` into the repo as `data/ml_model/re_ml_v9_fleet.pkl` (+ meta),
run deliberately before a push — never automatically, or every retrain churns
the repo. It arrives on a client with the ordinary `git pull` the updater
already does. 181 KB a time, so exporting on each release is a few MB of
history a year.

**Load, as a THIRD model.** The client must not refit the fleet model with its
own rows — `_train_batch` rebuilds from scratch every 5 labelled signals, so
the fleet's learning would be gone within 25 trades. Instead `predict()` gains
a third term:

```
fleet (LightGBM, read-only)   weight  w_fleet
local batch (LightGBM)        weight  0.6 * (1 - w_fleet)
local online (SGD)            weight  0.4 * (1 - w_fleet)
```

`w_fleet` starts at 1.0 — a brand-new client runs entirely on the fleet, which
is the day-one benefit asked for — and decays toward 0 as the client
accumulates its own labelled signals. That is how "their own training still
counts" is honoured without amalgamating anything: nothing is merged, the
client's own judgement simply takes over.

The decay curve is the one number to choose. Reaching w_fleet ~ 0.5 at around
100 of the client's own labelled signals matches the shape of option B in the
original decision (fleet as a prior, local overriding it) without needing the
rows.

**Optionally, the online model can be seeded** from the fleet's
`re_ml_online.pkl` instead of starting blank, since SGD *can* continue from
foreign state. Cheap, and it gives a new client a sensible starting slope. It
is a nice-to-have, not the mechanism.

## What this costs, against shipping rows

Each of the original four objections, and what it turns into:

1. **It is not the path that already exists.** Rows would have slotted into
   `_collect_training_data` with no new machinery. This needs a third model
   held in memory, a weight that changes over time, and `predict()` reworked —
   the function that decides which trades the ML gate allows.
2. **Weights die on a version bump, and the bump is routine.** `_version` is
   `re_ml_v9`; `ml_handover.py` exists precisely because bumps happen and
   discard fitted models. A fleet model stamped v9 must be **ignored** by a
   client on v10 — silently and correctly — until someone exports a v10 model.
   So "as it develops" is a **recurring release chore**, not a one-off: every
   feature change needs a fresh export or the fleet model quietly stops
   applying. Shipped rows would have survived the bump by padding.
3. **Nothing amalgamates.** A client ends up with the fleet's judgement and its
   own side by side, mixed at predict time by a weight somebody picked. That is
   not the same as one model that learned from both, and it cannot be evaluated
   as cleanly — there is no single training set to score.
4. **Privacy is better, and that is the point.** No rows leave. The model still
   encodes your trades statistically — that is what a model is — but nothing
   about any individual trade is recoverable from it in practice.

## Still true: not yet

Unchanged by the answer. `mean_r` is **-0.083** at every retrain: today's model
has correctly learned that the engine's own signals lose money. Shipping it
fleet-wide would install that conclusion on every client, and
[020](020-losses-exceed-the-stop.md), [030](030-wins-are-cut-at-two-thirds-of-a-r.md)
and [040](040-filter-the-instant-fills.md) are specifically about changing what
it would learn. Build the mechanism whenever; **export the first fleet model
after those land.**
