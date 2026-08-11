# First-impression review: the two database files and the Reversal Engine

*Written 2026-08-11, from a cold read of the code plus a direct inspection of
`data/forex_trader_demo.db` and `data/reversal_engine.db`. Written for a
reader who is new to the system — no prior knowledge assumed.*

---

## 1. What the two files are

| File | Size | What it is |
|---|---|---|
| `forex_trader_demo.db` | ~4.9 MB | The **main application database** from a demo-account run: Telegram messages, parsed signals, simulated and real (demo) trades, all settings. 38 tables. |
| `reversal_engine.db` | ~2.1 MB | The **Reversal Engine's private database**: every signal it invented itself, the price levels it watched, its virtual bank balance, and its attempts to match its own signals against the real Telegram channel. 15 tables. |

They cover the same period: **21–31 July 2026**, trading gold (XAUUSD) around
the $3,300–$4,070 price area, on a demo account that started with roughly
**$1,000**.

Each research engine keeps its own isolated SQLite file on purpose (that's a
documented rule of the system), which is why the Reversal Engine's data is not
inside the main file.

---

## 2. The big picture — how the pieces fit

The system has two fundamentally different ways of producing trades:

1. **Copying Telegram signals.** People in paid Telegram channels ("Gold
   Diggers VIP", "GOLD DIGGERS INSTITUTIONAL", "Gold Diggers Scalping") post
   messages like:

   ```
   Direction: BUY
   Currency: XAUUSD
   ENTRY : 4068-4070
   TP1: 4072  TP2: 4074  TP3: 4076 ...
   ```

   The app reads those messages (1,893 of them are stored in
   `telegram_messages`), parses out the numbers, and can trade them.

2. **Generating its own signals.** Three in-house "research engines" (Bounce,
   Breakout, **Reversal**) watch the live gold price directly and invent
   their own signals, with no Telegram input at all.

The Reversal Engine is the bridge between those two worlds, and that is the
part you asked about.

---

## 3. What the Reversal Engine is trying to do

**In one sentence: it is trying to learn to *be* the Gold Diggers VIP channel
— to predict the same trades the channel will post, but fire them *before*
the channel does.**

Your instinct in `000-initial.md` was right: it is "trying to understand
those signals". Concretely, it works like this (the code is in
[backend/src/services/reversal_engine/](../../../backend/src/services/reversal_engine/),
main orchestrator
[reversal_engine_service.py](../../../backend/src/services/reversal_engine/reversal_engine_service.py)):

1. **Find levels** (every 60 seconds). It scans recent price candles for
   prices where gold tends to bounce or reverse: the overnight Asia-session
   high/low, recent swing highs/lows, round numbers ($4,050, $4,045…),
   congestion zones, and one fancier "Unicorn" pattern from ICT trading
   theory ([level_detector.py](../../../backend/src/services/reversal_engine/level_detector.py),
   `ict_patterns.py`). The theory: the VIP channel's trader keys off these
   same levels, so if we watch them we should reach the same conclusions.

2. **Create a pending signal** when price approaches a good-enough level —
   an entry zone, a stop-loss, and a ladder of up to eight take-profit
   targets (TP1–TP8), deliberately shaped like the channel's own signals.
   A small machine-learning model, trained on the engine's own past
   outcomes, votes on which candidate level becomes the signal.

3. **Trigger and track it virtually.** When price enters the zone the signal
   "fills" at a simulated realistic price, and a 5-second loop then walks it
   through the TP ladder / stop-loss / break-even rules against the live
   price feed, settling profits and losses against a **pretend bank balance**
   (`virtual_balance` in `re_config`). No real money is involved in this
   tracking.

4. **Correlate against the real channel** (every 30 seconds). This is the
   "understanding" part. Each engine signal is compared with what the VIP
   channel actually posted. The key number, `correlation_time_delta_s`, is
   signed: **negative means the engine fired first (the goal), positive
   means it lagged.** Near-misses are logged too (`re_near_miss`), and a
   nightly AI job reads the day's channel messages and chart images and
   scores the channel trader's "discipline" and "aggression"
   (`re_daily_research`) — those scores feed back into the ML model.

5. **Optionally trade for real.** If its live-execution toggle is on (it
   *was* on in this data: `re_live_execution = 1`), a triggered signal is
   also sent to MT5 as a real order on the demo account, guarded by a
   circuit breaker, an R:R filter, exposure caps, and an ML veto.

The older `gdc_*` tables in the same file are a previous incarnation of the
same idea (a "Gold Diggers Copy" emulator); the `re_*` tables are the current
engine. Same design, half the columns renamed.

### Where your other two beliefs stand

- **"Signals only work at certain times of day"** — the engine agrees and
  partially encodes this. Its docs say the channel posts 04:00–16:00 UTC
  (measured from 591 real channel signals), and the stored messages confirm
  it: VIP posts cluster 05:00–14:00 UTC. The engine gates itself on the
  user-facing Asia/London/NY session toggles — but in this data **all three
  sessions were enabled**, so it effectively traded around the clock
  (signals exist in every hour from 00 to 23 UTC). More on whether that was
  wise in §5.
- **"Once it makes e.g. $300 in a day it stops"** — the feature exists but
  was **switched off** in this data: `profit_close_usd = 0.0`,
  `trading_schedule_enabled = 0`, daily target `0.0`. There is also a global
  "harvest" close-out at $75 (`global_harvest_threshold_usd = 75`) — also
  disabled. So nothing in these files ever stopped trading for the day
  because a target was reached.

---

## 4. What the data actually says

### 4.1 The Reversal Engine's own scoreboard (`reversal_engine.db`)

Nine days of running (23–31 July), 741 signals created:

| Outcome | Count | Total P&L | Average |
|---|---|---|---|
| Win | 429 | **+$9,661** | +$22.52 |
| Loss | 178 | **−$12,515** | **−$70.31** |
| Break-even | 7 | −$1 | — |
| Expired unfilled | 121 | $0 | — |
| Still open | 6 | — | — |

- **Win rate ≈ 70%, yet the book lost money.** The virtual balance started
  at $1,000 and ended at **−$1,887** — a paper loss of ~$2,900. The reason
  is plain in the averages: the typical loss ($70) is **three times** the
  typical win ($22.5). The sample signal in the data shows why: TP1 sits 3
  points from entry while the stop sits 7 points away (risk:reward 0.43:1).
  Lots of small wins, occasional large losses — arithmetic the win rate
  can't beat. The system's own live-execution R:R filter actually rejected
  some of these very signals ("TP1 is 3.0 pts from zone mid vs SL 7.0 pts
  away… minimum 0.75:1 required") — the *virtual* book has no such filter.

- **The core goal — predicting the channel — is not being achieved yet.**
  In `re_correlation`, `ref_predicted` (times we fired *before* the channel)
  is **0 on every single day**. Daily correlation rates run 0–19%: on the
  best day, 21 of 111 engine signals matched a channel signal at all. The
  engine trades a lot; it rarely coincides with the channel it is trying to
  imitate, and it never beat it to the punch in this sample.

- **It analyses far more than it fires.** Of 7,964 analysis-cycle logs:
  4,106 "no signal", 3,100 "session closed", 741 signals, 17 "no levels".

- **Level-type breakdown:** the two rarest sources are the only clear
  positives — `asia_high` (+$144 over 17 signals) and `unicorn` (+$182 over
  26). The high-volume sources all lost: `round_5` −$1,235 (211 signals),
  `congestion` −$805 (153), `round_10` −$459 (207). Round-number levels are
  ~56% of all signals and ~59% of the losses in dollars.

- **Live execution was on.** 157 signals became real demo-account MT5
  orders. Another ~450 were blocked by the guardrails — ML veto (117),
  momentum filter (96), exposure guard (111), circuit breaker (19), R:R
  filter (14), schedule/sig-guard/others (~60). The guardrails were doing a
  lot of work.

### 4.2 The main app's scoreboard (`forex_trader_demo.db`)

`consolidated_trades` (1,142 rows, 21–31 July) is the whole-app ledger across
every trade source:

| Source | Trades | Net P&L |
|---|---|---|
| Reversal Engine | 928 | **−$2,616** |
| Breakout Engine | 24 | −$785 |
| Gold Diggers VIP (copied) | 43 | −$703 |
| Bounce Engine | 56 | −$392 |
| Manual / other | 51 | −$382 |
| GOLD DIGGERS INSTITUTIONAL (copied) | 40 | **+$287** |
| **Total** | **1,142** | **≈ −$4,590** |

- Every single day was negative except 24 July (+$338). The worst days were
  29 July (−$1,142) and 31 July (−$1,322). The account's cached "heatmap"
  AI commentary in `app_config` opens, bluntly: *"This trader is bleeding
  out…"*.
- The only profitable source was copying the INSTITUTIONAL channel — small
  sample (40 trades), but notable.
- The demo simulation account sits at $906 from a $1,000-ish start;
  `peak_balance` was $2,140, so there was a real drawdown of over half from
  the peak.

### 4.3 Time of day — your hunch, tested

Whole-app P&L by hour the trade was opened (UTC), 10 days of data:

- **Consistently bad:** 12:00–16:59 UTC (−$3,398 across ~375 trades — the
  NY-morning block is the biggest sinkhole), 19:00 (−$1,093), 01:00–02:59
  (−$1,252), 07:00 (−$547), 22:00 (−$392).
- **Consistently decent:** 18:00 (+$880), 03:00 (+$412), 11:00 (+$349),
  00:00 (+$343), 17:00 (+$151).

The Reversal Engine's own per-hour numbers show the same shape (12:00–16:00
and 19:00 UTC are its worst hours). So the data *supports* the "only works at
certain times" belief — but note the feature built for exactly this,
`hour_blocklist_enabled`, was **off**, and all three session toggles were on.
The engine's docstring says the reference channel is 72% active 07:00–14:59
UTC — yet that busy window is where the losses concentrate, which is
consistent with the channel's own aggressive midday style (the nightly AI
research repeatedly describes it "buying into a falling market", discipline
scores 0.3–0.75).

### 4.4 Data-quality observations (worth knowing before trusting any report)

1. **Numbers disagree between tables.** `channel_performance` says the
   Reversal Engine is **+$708 (63.7% win rate)** while `consolidated_trades`
   says **−$2,616** and its own DB says **−$2,876** of virtual losses. These
   tables measure different things (real fills vs. virtual ladder vs. a
   rolling window), but a novice reading one screen could get the opposite
   impression of the truth. Treat `consolidated_trades` + `re_balance_log`
   as the honest ledgers.
2. **Probable double-counting in `consolidated_trades`.** Many trades appear
   twice with identical P&L a few seconds apart (e.g. +$34.03/+$34.03,
   −$50.00/−$50.00 pairs throughout). 928 "Reversal Engine" rows vs. 614
   under `engine='reversal_engine'` also hints at overlap between the
   `tg_source` and `engine` labelling. The −$4,590 total may therefore be
   overstated (the *direction* of every conclusion above survives, but the
   magnitudes need a dedup pass before being quoted).
3. **The virtual balance goes negative (−$1,887)** — a real account would
   have been stopped out long before; the simulation has no margin/ruin
   check, so tail losses keep compounding into the stats the ML learns from.
4. **Credentials live in these files.** `mt5_credentials`,
   `telegram_config`, and `email_config` contain (encrypted) logins and
   API-key columns. These .db copies are sitting in a docs folder — worth
   confirming they're demo-only and not committed anywhere public.
5. Minor: `re_correlation.avg_lead_time_s` is NULL on every row — the
   headline "lead time" metric is never being aggregated, so the engine's
   main success measure isn't visible anywhere.

---

## 5. First-impression verdict

The **code** is genuinely thoughtful — session gates, ATR gates, cooldowns,
loss streaks, circuit breakers, an ML re-check before live fills, signed
lead-time correlation, and honest internal commentary about past bugs. The
guardrails visibly fired hundreds of times in this data and saved money.

The **strategy**, on this 9-day sample, is not working yet:

1. **The risk:reward is upside-down.** Avg loss 3× avg win kills a 70% win
   rate. The live R:R filter (min 0.75:1) knows this; the signal *generator*
   still produces 0.43:1 signals. Fixing signal geometry (or letting the
   R:R filter veto signal *creation*, not just live execution) is the single
   highest-leverage change the data points to.
2. **The emulation isn't emulating.** 0 predicted channel signals ever, and
   correlation under 20% on the best day. As a *predictor of the channel*
   it currently fails; as a *standalone level-trading strategy* it loses.
   The near-miss table (145 rows) is where to look for why matches fail.
3. **The protective features you believed were on, were off**: daily profit
   target ($300-style stop), hour blocklist, harvest close-out, risk
   governor, unattended mode — all disabled in this snapshot. The by-hour
   data suggests the hour blocklist alone (block 12–16 and 19 UTC) would
   have removed the majority of the losses.
4. **Only two things made money**: copying the INSTITUTIONAL channel
   (+$287) and the engine's rare `asia_high` / `unicorn` level types. Small
   samples, but they're the threads worth pulling.

### Sensible next steps (no code changed yet — for discussion)

1. Dedup `consolidated_trades` and re-run the P&L/hour numbers so the
   magnitudes are trustworthy.
2. Decide (Simon question?) whether the daily target, hour blocklist and
   risk governor *should* have been on — and if yes, why they were off.
3. Look at signal geometry: why TP1 lands at 0.43:1 against a 7-point stop,
   and whether the generator should refuse sub-0.75:1 signals outright.
4. Dig into `re_near_miss` to understand why engine signals miss the
   channel's — direction, distance, or timing.

*Questions that are trading-policy calls (targets, sessions, whether the
engine should trade live at all) belong in `docs/simon-handover/` per
CLAUDE.md — flagged here, not decided here.*
