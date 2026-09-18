# 010 — Stage 0 + Stage 1: the Telegram decision log

Built 2026-09-18 from [000](000-validating-a-telegram-signal-before-execution.md).
**Recording only. No trade decision changes.** One toggle on the Parsing page
turns the whole thing on and off; with it off, not a line of this runs.

## What it records

One row per Telegram signal that reaches an execution decision — executed or
blocked, on the full-signal path and on the IME path — carrying the market as
it was at that instant, which gate actually decided it, and, filled in later,
what our trade really did.

Two tables in `reversal_engine.db`, not the core DB, for the reason
`pro_corpus_repo` documents: the core DB is per-environment
(`forex_trader_demo.db` / `forex_trader_live.db`), so a corpus kept there
splits in half the day the account switches. `account_env` is a column
instead, so demo and live can be separated at analysis time rather than by
accident.

- **`tg_decisions`** — the decision and its context. `UNIQUE(tg_message_id,
  path)`, INSERT OR IGNORE, so a rescan cannot double-count.
- **`tg_shadow_decisions`** — one row per variant per decision.
  `UNIQUE(decision_id, variant)`.

## The one-fact-set rule

Every shadow fact is computed **before** any gate returns, and the row is
written at whichever exit is taken carrying that same fact set. This is
`reversal_engine_live_execute.py`'s rule, quoted because it was learned the
expensive way: recording at each early return instead would record "would
take" for a variant whose later gates never ran, which reads as an
endorsement it never gave.

## Stage 1 variants

| Variant | Fact | Where it comes from |
|---|---|---|
| `live (champion)` | what actually happened | the live path |
| `session liquidity` | rollover / weekend-reopen window | `session_liquidity.check(decided_at)` — pure clock, exact |
| `event tier` | a calendar event inside its tier window | `event_tiers.check` over the same calendar `check_news_blackout` already reads |
| `spread guard` | spread at decision time | recorded inline on both paths |
| `confirmed entry` | the entry trigger | replayed from `candles_range` ending at the decision |
| `trend (HTF bias)` | H1 bias | `governor.current_htf_bias`, evaluated in the background sweep |

**The spread costs nothing on either path, and that is measured rather than
assumed.** `mt5_client.get_tick()` caches for 1.0s and the wrapper's read
happens before the body's, so on an executing decision the body's read becomes
the cache hit and the round-trip count is unchanged. On a decision blocked
before the body ever asks it is one localhost call, on a path that is not
latency-critical by definition.

**The entry trigger is replayed, not re-read.** `candles_range(decided_at -
30m, decided_at)` gives the bars that existed at the decision, so the variant
sees the moment rather than the present. That also means it has **no freshness
limit** -- unlike the bias, a decision from last Tuesday is exactly as
scoreable as one from a minute ago, which is what makes the backfill worth
anything.

An unavailable fact **abstains** — `would_take` NULL, never False. That is
`shadow.decide`'s rule: a challenger that blocked on a fact it never had
would report a refusal rate that says nothing.

## Latency

Nothing is fetched on the decision path. The inline facts are a clock read,
a cached-calendar read and numbers already in hand. The measured IME budget
is 269 ms end to end, 256 ms of it the broker POST, so this must stay in the
noise — and it does.

The H1 bias and the outcome fill run in the background sweep,
`core_signal_snapshot.run_snapshot_cycle`, which already hosts three cadences
of exactly this kind. The bias is read within the 60s resolve window and the
live path's own bias cache has the same 60s TTL, so it is contemporaneous to
the same tolerance the live gate accepts — recorded with its lag so that is
auditable rather than assumed.

## What shipped

| File | What it is |
|---|---|
| `signals/decision_log_repo.py` | the two tables and every statement that touches them |
| `signals/decision_log.py` | `enabled` / `inline_facts` / `record` -- the decision-path half |
| `signals/decision_shadow.py` | variants, `decide`, `evaluate_pending`, `report` |
| `signals/decision_outcomes.py` | `resolve_pending` against the trade ledger |
| `signals/decision_backfill.py` | rebuilding decisions from past trades |
| `signals/tg_repo.telegram_trades_for_backfill` | the one query that joins a trade back to its message |
| `telegram_controller` | three reads and one action, one service call each |
| `telegram/_decision_log.py` | the readout card |
| migration 47 | `tg_decision_log_enabled`, default 0 |
| `telegram/_keywords.py` | the switch, Parsing page, RESEARCH group |
| `core_signal_snapshot.run_snapshot_cycle` | a fourth cadence, 60s, failure-isolated |
| `app.py` | `create_schema()` at startup |

Call sites: `scan_auto_execute.execute_auto_signal` (a wrapper around the
unmodified body) and `instant_entry.process_instant_entry` (eleven exits, one
recorder, control flow untouched).

## Rebuilding the past

`decision_backfill.run()` reconstructs a decision for every closed
Telegram-sourced trade, joined back to its message through
`vantage_signals.signal_id`. It exists because the log otherwise needs four to
six weeks at this account's volume before a variant has anything to say, and
most of that wait is avoidable.

**Exact, not approximated:** session liquidity is arithmetic on a timestamp,
and the entry trigger replays the candles of that moment. Both give the answer
the live gate would have given.

**Gone, and recorded as gone:** the calendar as it stood, and the HTF bias,
which was a live read. Both abstain.

**Close but not the same measurement:** the spread comes from
`trade_spread_cache`, which is the spread on the fill rather than the quote
the guard would have read moments earlier.

Every rebuilt row carries `source='backfill'`. A table where reconstructions
and observations are indistinguishable is one nobody can trust twice.

**Only executed trades.** Nothing recorded what was blocked before the log
existed, and a block cannot be inferred from an absence. Inventing them would
hand every challenger a pile of avoided losses it never earned. So a rebuilt
corpus answers one question, which happens to be the useful one: of the trades
this account actually took, which would each gate have stood aside from?

## Reading it

Parsing page, under the toggle. Two readouts, useful at different times.

**What happened** works from the first decision: totals, executed vs declined
per path, and the ranked reasons for declining. Nothing has to close.

**Champion vs challenger** needs closed trades, and is the point of the
exercise. A variant that has scored nothing reads "no decisions yet" rather
than 0.000 -- `report()` returns `mean_r` as None precisely so the page can
tell those apart.

Both on a button, not a timer: this sits under a live trading page and the
numbers move twice a day.

## Retention: deliberately none

Neither table is pruned, and neither is `pro_snapshots`. `db/retention.py`
covers the core database only, and that is the right shape -- you do not prune
a training corpus, and a study whose early rows silently vanish is a study
that quietly changes its answer. At a few dozen rows a day this costs nothing
worth measuring. Recorded here as a decision so it does not get read later as
an oversight.

## Outcomes

Filled by a sweep joining `vantage_simulated_trades` on `trade_id`:
`realised_r = net_pnl / initial_risk` (populated on all 401 closed trades as
of 2026-09-18), plus `net_usd`, `max_tp_hit` and `exit_reason`.

**Nothing hooks the close path.** That path is frozen, and a research log has
no business on it.

## What it is for

After 2-4 weeks, `report()` gives per variant: taken, skipped, net $, mean R.
That is the evidence stage 2 needs to promote a gate — or to decline to.
