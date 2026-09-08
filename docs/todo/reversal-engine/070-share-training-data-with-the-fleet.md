# 070 — Ship the fleet's learning to every client, without losing theirs

**Status:** designed 2026-09-08, **one decision needed before building.**
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
