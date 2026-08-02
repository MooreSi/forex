# Configuration audit — what is configurable, where it lives, what isn't

Written 2026-08-02, prompted by Q3 ("things like the risk ceiling should all
be configurable — we need to look at what can be configured and how we store
it"). Status: **inventory + recommendation. No changes made yet.**

## 1. The storage mechanisms that exist today

There are **nine** places a setting can live. Each exists for a reason, but
nothing documents which tier a new setting should go in — that is why
tunables keep ending up as hardcoded constants instead.

| # | Mechanism | Where | Scope & sync | Edited via |
|---|---|---|---|---|
| 1 | `config.yaml` | `~/.config/ForexTrader/config.yaml` (per-OS data dir) | **Per machine.** Never synced | Settings page / hand-edit |
| 2 | `vantage_risk_settings` | main DB, singleton row, ~60 columns | Per environment (demo/live). **Synced** to the paired node | Trading & Telegram pages |
| 3 | `app_config` | main DB, key/value, ~34 keys | Per environment. Mostly **not** synced (sync_* keys, schedule are) | Various pages |
| 4 | `vantage_fee_settings` | main DB, singleton row, 8 columns | Per environment | Settings page |
| 5 | `email_config` / `telegram_config` / `mt5_credentials` | main DB, singleton rows | Per environment | Settings page |
| 6 | Strategy Parameters | `PARAM_SPECS` catalogue (risk/strategy_params.py) + DB override + saved templates | Per environment, synced | Trading page (generic UI from the catalogue) |
| 7 | Adaptive params | per-engine catalogue with default/min/max/desc, stored in each engine's own DB | Per engine | AI-tuned (clamped), visible in panels |
| 8 | Per-channel config | `channel_parser_config`, learned rules, strategy overrides | Per environment | Telegram/Trading pages |
| 9 | EA trade templates | `ea_trade_templates` | Per environment | Settings page |

What each tier is FOR (implicit today, should be the written rule):

- **yaml (1)** — machine identity & bootstrap only: paths, env, API keys,
  bridge URL. Things needed *before* the DB opens. Never trading behavior.
- **risk_settings (2)** — trading behavior the user flips: sizing, limits,
  strategy, toggles. Synced because both nodes must agree.
- **app_config (3)** — operational state and misc persistence: pause-until,
  last-email markers, caches, sync wiring. A junk drawer; acceptable for
  state, wrong for behavior tunables.
- **catalogued params (6/7)** — the two GOOD patterns (see §4).

## 2. What is already configurable (the good news)

Q3's specific worry is already covered: `risk_per_trade_pct`,
`max_risk_per_trade_pct`, `max_lot_size`, `default_lot_size`,
`strategy_lot_size` are all live UI settings in `vantage_risk_settings`.
So are: daily-loss/drawdown limits, max open trades, circuit breaker
(enabled/losses/cooldown), session toggles, hour blocklist, out-of-hours
strategy, Kelly sizing, global harvest, DPM knobs, ORB auto-execute + lot,
per-engine live-execution switches, all Logic-Keyword toggles, trailing
distance, BE-after-TP1, cooldowns, trading schedule (7×3 windows with
per-source gates), fees/slippage/swap, data retention, and 11 strategies ×
~4-6 tunables each via Strategy Parameters with save/load templates.

## 3. What is NOT configurable but is a behavior tunable

The sweep found **~135 module-level numeric constants in `backend/src/services/`
alone**, plus function-local ones. They fall into three tiers:

**Tier A — trades differently if changed; a trader might genuinely want to
tune these** (the strongest candidates to expose):

| Constant | Value | Where | What it does |
|---|---|---|---|
| `_MIN_RR` | 0.75 | risk/governor.py (pre-trade filter) | Minimum TP1 R:R to open at all |
| `RG_MIN_TP1_RR` / `RG_MAX_STOP_ATR` | 1.00 / 1.5 | risk/governor.py (governor sizing) | R:R floor and stop-width cap |
| `_MAX_UNPROTECTED` | 2 | risk/governor.py | Directional cap on unprotected same-direction trades |
| `RR_BYPASS_SOURCES` | 2 channels | risk/governor.py | Channels exempt from the R:R filter |
| IME SL bounds | 8..25 pts, ATR×1.2 | trading/instant_entry.py | Provisional stop for instant entries |
| `_IME_TIMEOUT_SEC` | 180 | trading/instant_followup.py | How long an instant trade waits for its SL/TP follow-up |
| `_EXPIRY` | 120 s | signals/pending_activation.py | Queued signal dies if zone not refilled in time |
| `_MAX_SIGNAL_AGE_SECS` | 240 s | signals/scan_staleness.py | Older signals are recorded, never executed |
| `_RECENT_DUP_WINDOW` | 15 min | signals/scan_parse_classify.py | Duplicate-signal suppression window |
| `MT5_SYNC_MISS_THRESHOLD` | 2 cycles | runtime.py | Missing-ticket streak before a trade is treated as broker-closed |
| TP ladder fractions | per-count dicts | positions/ + backtest | How much closes at each TP (Reversal Runner / Climber) |
| `signal_bus` TTL | 300 s | cluster/signal_bus_repo.py | Cross-engine agreement window |

**Tier B — engine-internal calibration** (cycle intervals, ADX/ATR band
edges, swing lookbacks, correlation windows, ML retrain cadence, consec-loss
guards). Legitimate constants for most users, but they are exactly the class
the adaptive-params catalogue already handles for other values — extending
that catalogue is cheap.

**Tier C — leave hardcoded** (protocol values, display constants, contract
size, broker TZ offset, dedup keys, group IDs*).
*The hardcoded Telegram group IDs (`_REF_GROUP_ID` etc. in the reversal
engine) are arguably Tier A — they hard-wire the app to two specific paid
channels. Flagged for the owner.

## 4. Recommendation

The codebase already contains the right pattern **twice**:

- `PARAM_SPECS` (strategy params): `(key, label, default, unit)` catalogue →
  generic UI rendering → DB override merged over defaults → synced →
  cache-invalidated on env switch → unknown keys rejected.
- `adaptive_params.PARAMS`: adds `min`/`max`/`desc` and clamping.

**Proposal — one declarative catalogue per domain, same shape everywhere:**

1. Add an `EXPERT_PARAMS` catalogue (key, label, default, min, max, unit,
   desc, domain) for the Tier-A list above, stored as a DB override merged
   over defaults exactly like strategy params (same code path, same sync,
   same cache invalidation — mostly reuse).
2. Render it generically on a new **Settings → Expert Tunables** section,
   grouped by domain, each control showing default + safe range, with a
   "reset to default" per row. No bespoke UI per setting ever again.
3. Write the tier rule down (the table in §1) in CONTRIBUTING/docs so a new
   tunable lands in the catalogue by default instead of as a constant.
4. Tier B migrates opportunistically into each engine's existing
   adaptive-params catalogue (marked "manual" so the AI tuner won't touch
   them unless allowed).
5. Explicitly NOT recommended: making all 135 constants configurable. Most
   are calibration with test-verified interactions; exposing them all makes
   the safe envelope meaningless. Tier A is ~15 settings; start there.

**Safety note:** several Tier-A values gate order placement (R:R floor,
directional cap, miss-threshold). Exposing them is a behavior change to the
risk envelope only when the user moves them — defaults stay identical — but
the UI should mark them clearly and the demo-account session should include
a pass over this page.

## 5. Decisions for the owner

1. Approve the Expert Tunables approach (§4) and the Tier-A starter list?
2. Should the two hardcoded Telegram group IDs become channel config?
3. Ranges: for each Tier-A value, what min/max is *safe*? (I can propose
   defaults from the code's own comments, but the envelope is a trading
   judgement.)
