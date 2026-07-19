"""
Unified SQLite database layer.
Single DB file combines trading engine schema and Telegram reader schema.
Schema is column-compatible with the source services for data migration.
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DB_PATH: str = ""

# Every db() call in this module runs synchronously and, historically, always
# on the single asyncio event-loop thread — fine when the underlying disk I/O
# is fast, but with no application-level bound when it isn't (VPS disk stalls
# were the likely cause of the multi-minute event-loop freezes seen in
# production). A single dedicated worker thread (not asyncio.to_thread's
# default shared pool, which would hand different calls to different threads
# non-deterministically) lets hot-path callers move DB work off the event
# loop while preserving today's fully-serialized, one-thread-touches-the-file
# access pattern — no new concurrent-connection/lock-contention risk is
# introduced, since it's always this same one thread issuing every call.
_db_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="db-worker")

# The main asyncio event loop, captured once at startup (see set_main_event_loop
# below) so code running on the DB worker thread — or any other non-main
# thread — can still schedule a coroutine onto it. Needed because
# update_risk_settings() -> _forward_settings_over_sync() tries to schedule
# an asyncio task (propose_settings/broadcast_settings); asyncio.ensure_future()
# only works on the thread that's actually running the target loop, so once
# to_db_thread() started moving more DB-writing calls off the event-loop
# thread, any of them that touch update_risk_settings() (e.g.
# record_live_trade_outcome() after a circuit-breaker update) silently failed
# to forward the change to the paired node — "RuntimeWarning: coroutine ...
# was never awaited", not a raised exception, so nothing surfaced this until
# settings visibly diverged between the two nodes.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


async def to_db_thread(fn, *args, **kwargs):
    """Run a synchronous database.py call on the dedicated DB worker thread
    instead of blocking the caller's own event-loop thread. Use this at
    call sites that run frequently (tight loops, hot paths) where a slow
    disk I/O moment would otherwise stall the entire application."""
    loop = asyncio.get_running_loop()
    if kwargs:
        import functools
        fn = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(_db_executor, fn)
    return await loop.run_in_executor(_db_executor, fn, *args)

# One connection per thread, reused for the thread's lifetime, instead of a
# fresh sqlite3.connect()/close() on every single db() call. This codebase
# calls db() extremely frequently — often several times per open trade per
# UI refresh timer tick — and opening/closing a connection each time is real,
# measurable synchronous work on the single asyncio event-loop thread (worse
# on Windows, where antivirus/Defender real-time scanning commonly intercepts
# each file-handle open). That was directly implicated in event-loop stalls
# of 400-600ms attributed to nicegui timer callbacks on the VPS. Safe to
# reuse across calls from the same thread: check_same_thread=False was
# already set, and every caller goes through this context manager, which
# always commits or rolls back before yielding control back.
_thread_local = threading.local()


def init(db_path: str) -> None:
    global _DB_PATH
    _DB_PATH = db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _apply_schema()


@contextmanager
def db():
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        _thread_local.conn = conn
    # Nesting depth so a re-entrant db() call (a function that itself calls
    # db() while already inside another db() block, on the same thread)
    # doesn't commit/rollback the shared connection out from under the
    # outer block before it's done — only the outermost caller actually
    # finalizes the transaction; inner ones just pass the same connection
    # through untouched.
    depth = getattr(_thread_local, "depth", 0) + 1
    _thread_local.depth = depth
    try:
        yield conn
        if depth == 1:
            conn.commit()
    except Exception:
        if depth == 1:
            conn.rollback()
        raise
    finally:
        _thread_local.depth = depth - 1


def row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row)


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS mt5_credentials (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    login         INTEGER NOT NULL,
    password_enc  TEXT    NOT NULL DEFAULT '',
    server        TEXT    NOT NULL DEFAULT '',
    terminal_path TEXT,
    account_type  TEXT    NOT NULL DEFAULT 'demo',
    updated_at    REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mt5_connection_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL    NOT NULL,
    event_type TEXT    NOT NULL,
    detail     TEXT
);

CREATE TABLE IF NOT EXISTS vantage_signals (
    signal_id     TEXT PRIMARY KEY,
    source_name   TEXT NOT NULL DEFAULT '',
    direction     TEXT NOT NULL,
    entry_low     REAL NOT NULL,
    entry_high    REAL NOT NULL,
    stop_loss     REAL NOT NULL,
    tp1           REAL,
    tp2           REAL,
    tp3           REAL,
    tp4           REAL,
    tp5           REAL,
    tp6           REAL,
    tp7           REAL,
    tp8           REAL,
    lot_size      REAL,
    risk_pct      REAL,
    notes         TEXT DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    REAL NOT NULL,
    activated_at  REAL,
    cancelled_at  REAL,
    claude_commentary TEXT
);

CREATE TABLE IF NOT EXISTS vantage_simulated_trades (
    trade_id          TEXT PRIMARY KEY,
    signal_id         TEXT NOT NULL,
    mt5_ticket        INTEGER,
    direction         TEXT NOT NULL,
    entry_low         REAL NOT NULL,
    entry_high        REAL NOT NULL,
    entry_price       REAL NOT NULL,
    lot_size          REAL NOT NULL,
    remaining_lots    REAL NOT NULL,
    stop_loss         REAL NOT NULL,
    tp1               REAL,
    tp2               REAL,
    tp3               REAL,
    tp4               REAL,
    tp5               REAL,
    tp6               REAL,
    tp7               REAL,
    tp8               REAL,
    status            TEXT NOT NULL DEFAULT 'open',
    open_time         REAL NOT NULL,
    close_time        REAL,
    close_price       REAL,
    exit_reason       TEXT,
    gross_pnl         REAL NOT NULL DEFAULT 0,
    realised_pnl      REAL NOT NULL DEFAULT 0,
    spread_cost       REAL NOT NULL DEFAULT 0,
    commission        REAL NOT NULL DEFAULT 0,
    swap_est          REAL NOT NULL DEFAULT 0,
    slippage_cost     REAL NOT NULL DEFAULT 0,
    net_pnl           REAL NOT NULL DEFAULT 0,
    claude_open       TEXT,
    claude_close      TEXT,
    telegram_status   TEXT,
    sl_moved_to_be    INTEGER NOT NULL DEFAULT 0,
    strategy          TEXT NOT NULL DEFAULT 'scale_out',
    mt5_profit        REAL,
    tg_source         TEXT,
    FOREIGN KEY (signal_id) REFERENCES vantage_signals(signal_id)
);

CREATE TABLE IF NOT EXISTS vantage_partial_closes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id      TEXT NOT NULL,
    ts            REAL NOT NULL,
    lots_closed   REAL NOT NULL,
    close_price   REAL NOT NULL,
    pnl           REAL NOT NULL,
    reason        TEXT NOT NULL DEFAULT 'TP',
    FOREIGN KEY (trade_id) REFERENCES vantage_simulated_trades(trade_id)
);

-- Adaptive Runner's TP ladder as genuine resting broker-side orders: each
-- tier is its own separate MT5 position (hedging-mode account, confirmed
-- 2026-07-17) with its own native TP, so profit banks atomically at the
-- broker the instant price touches it -- not via Python noticing a crossed
-- tick, which a fast multi-point spike-and-reverse can miss entirely (see
-- project_adaptive_runner_ladder memory for the root-cause analysis).
-- One vantage_simulated_trades row (the "parent") still represents the whole
-- logical position for History/reporting; its own mt5_ticket is the anchor
-- (tier 1) leg for backward-compatible ticket-keyed lookups.
CREATE TABLE IF NOT EXISTS vantage_ladder_legs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id      TEXT NOT NULL,
    tier          INTEGER NOT NULL,
    tp_num        INTEGER NOT NULL,
    tp_price      REAL NOT NULL,
    lots          REAL NOT NULL,
    entry_price   REAL,
    mt5_ticket    INTEGER,
    status        TEXT NOT NULL DEFAULT 'open',
    close_price   REAL,
    close_time    REAL,
    pnl           REAL,
    FOREIGN KEY (trade_id) REFERENCES vantage_simulated_trades(trade_id)
);
CREATE INDEX IF NOT EXISTS idx_ladder_legs_trade ON vantage_ladder_legs(trade_id);

CREATE TABLE IF NOT EXISTS vantage_simulation_account (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    balance       REAL NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'USD',
    reset_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_config (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    bot_token_enc TEXT NOT NULL DEFAULT '',
    chat_id       TEXT NOT NULL DEFAULT '',
    enabled       INTEGER NOT NULL DEFAULT 0,
    updated_at    REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vantage_risk_settings (
    id                            INTEGER PRIMARY KEY CHECK (id = 1),
    risk_per_trade_pct            REAL    NOT NULL DEFAULT 0.5,
    max_risk_per_trade_pct        REAL    NOT NULL DEFAULT 1.0,
    max_daily_loss_pct            REAL    NOT NULL DEFAULT 3.0,
    max_total_drawdown_pct        REAL    NOT NULL DEFAULT 8.0,
    max_open_trades               INTEGER NOT NULL DEFAULT 1,
    max_pending_signals           INTEGER NOT NULL DEFAULT 10,
    default_lot_size              REAL    NOT NULL DEFAULT 0.01,
    max_lot_size                  REAL    NOT NULL DEFAULT 0.10,
    require_sl_and_tp             INTEGER NOT NULL DEFAULT 1,
    require_at_least_tp1          INTEGER NOT NULL DEFAULT 1,
    allow_no_sl                   INTEGER NOT NULL DEFAULT 0,
    move_sl_to_be_after_tp1       INTEGER NOT NULL DEFAULT 1,
    pause_after_losses            INTEGER NOT NULL DEFAULT 3,
    cooldown_after_loss_min       INTEGER NOT NULL DEFAULT 15,
    auto_execute_signals          INTEGER NOT NULL DEFAULT 0,
    trade_strategy                TEXT    NOT NULL DEFAULT 'scale_out',
    trailing_stop_distance        REAL    NOT NULL DEFAULT 5.0,
    strategy_lot_size             REAL    NOT NULL DEFAULT 0.0,
    immediate_market_entry        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vantage_fee_settings (
    id                            INTEGER PRIMARY KEY CHECK (id = 1),
    account_type                  TEXT    NOT NULL DEFAULT 'custom',
    commission_per_lot_per_side   REAL    NOT NULL DEFAULT 0.0,
    commission_round_turn_per_lot REAL    NOT NULL DEFAULT 0.0,
    include_spread_cost           INTEGER NOT NULL DEFAULT 1,
    include_swap_cost             INTEGER NOT NULL DEFAULT 1,
    estimated_slippage_points     REAL    NOT NULL DEFAULT 5.0,
    max_allowed_spread_points     REAL    NOT NULL DEFAULT 50.0,
    swap_per_lot_per_night        REAL    NOT NULL DEFAULT -6.5
);

CREATE TABLE IF NOT EXISTS vantage_claude_commentary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id     TEXT,
    signal_id    TEXT,
    ts           REAL NOT NULL,
    event_type   TEXT NOT NULL,
    payload      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vantage_telegram_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL    NOT NULL,
    event_type   TEXT    NOT NULL,
    trade_id     TEXT,
    status       TEXT    NOT NULL,
    detail       TEXT
);

CREATE TABLE IF NOT EXISTS vantage_tg_signals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_message_id  TEXT NOT NULL UNIQUE,
    group_id       TEXT NOT NULL,
    group_name     TEXT,
    sender_name    TEXT,
    message_ts     TEXT,
    raw_text       TEXT NOT NULL,
    parsed_at      REAL NOT NULL,
    direction      TEXT,
    entry_low      REAL,
    entry_high     REAL,
    stop_loss      REAL,
    tp1            REAL,
    tp2            REAL,
    tp3            REAL,
    tp4            REAL,
    tp5            REAL,
    tp6            REAL,
    tp7            REAL,
    tp8            REAL,
    signal_id      TEXT,
    status         TEXT NOT NULL DEFAULT 'new'
);

CREATE TABLE IF NOT EXISTS vantage_bot_updates (
    update_id      INTEGER PRIMARY KEY,
    processed_at   REAL    NOT NULL,
    action         TEXT,
    result         TEXT
);

-- Telegram reader tables (merged from telegram-reader service)
CREATE TABLE IF NOT EXISTS telegram_messages (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_message_id   TEXT NOT NULL,
    group_id              TEXT NOT NULL,
    group_name            TEXT,
    sender_id             TEXT,
    sender_name           TEXT,
    timestamp             TEXT,
    received_at           TEXT,
    text                  TEXT,
    raw_text              TEXT,
    has_media             INTEGER,
    media_type            TEXT,
    reply_to_message_id   TEXT,
    forwarded             INTEGER,
    raw_json              TEXT,
    UNIQUE(telegram_message_id, group_id)
);

CREATE TABLE IF NOT EXISTS telegram_reader_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT,
    event_type   TEXT,
    status       TEXT,
    message      TEXT,
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS custom_strategies (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    base_strategy TEXT NOT NULL DEFAULT 'scale_out',
    rules_json    TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL
);

-- App config key/value store
CREATE TABLE IF NOT EXISTS app_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Per-position spread cache — computed once from historical MT5 ticks at
-- trade-open time, then reused forever (spread at a past moment never
-- changes). Keyed by position_id since Closed Trades reads directly from
-- MT5 deal history, not any one engine's own trade table.
CREATE TABLE IF NOT EXISTS trade_spread_cache (
    position_id      INTEGER PRIMARY KEY,
    spread_price     REAL NOT NULL,
    spread_points    REAL NOT NULL,
    spread_cost_usd  REAL NOT NULL,
    computed_at      REAL NOT NULL
);

-- DPM per-trade performance log — used for self-calibration and analysis
CREATE TABLE IF NOT EXISTS dpm_trade_performance (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id              TEXT UNIQUE NOT NULL,
    direction             TEXT,
    entry_price           REAL,
    close_price           REAL,
    lot_size              REAL,
    original_sl           REAL,
    exit_type             TEXT,       -- 'SL', 'BE', 'trail', 'TP', 'manual'
    final_pnl             REAL,
    r_multiple            REAL,
    hold_minutes          REAL,
    -- Market state at entry (first DPM cycle)
    atr_at_entry          REAL,
    session_at_entry      TEXT,
    momentum_at_entry     REAL,
    momentum_label        TEXT,       -- weak/moderate/strong
    regime_at_entry       TEXT,       -- trending/ranging/spike
    -- Parameters in effect at entry
    be_multiplier_used    REAL,
    trail_multiplier_used REAL,
    be_trigger_used       REAL,
    trail_dist_used       REAL,
    tp1_pct_used          REAL,
    -- Trade milestones
    reached_be            INTEGER DEFAULT 0,
    reached_tp1           INTEGER DEFAULT 0,
    reached_tp2           INTEGER DEFAULT 0,
    peak_pnl              REAL DEFAULT 0.0,
    -- Meta
    used_calibrated       INTEGER DEFAULT 0,   -- 1 if calibrated params were available
    adx_at_entry          REAL,
    tg_source             TEXT,
    opened_at             REAL,
    closed_at             REAL
);

-- DPM calibration history — each run produces one row per (session, momentum_bucket)
CREATE TABLE IF NOT EXISTS dpm_calibration (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrated_at   REAL NOT NULL,
    session         TEXT NOT NULL,
    momentum_bucket TEXT NOT NULL,
    be_multiplier   REAL NOT NULL,
    trail_multiplier REAL NOT NULL,
    tp1_partial_pct REAL NOT NULL,
    sample_size     INTEGER NOT NULL,
    profit_factor   REAL,
    win_rate        REAL,
    avg_r_multiple  REAL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS email_config (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    smtp_host          TEXT    NOT NULL DEFAULT '',
    smtp_port          INTEGER NOT NULL DEFAULT 587,
    smtp_user          TEXT    NOT NULL DEFAULT '',
    smtp_password      TEXT    NOT NULL DEFAULT '',
    from_addr          TEXT    NOT NULL DEFAULT '',
    to_addr            TEXT    NOT NULL DEFAULT '',
    use_tls            INTEGER NOT NULL DEFAULT 1,
    daily_enabled      INTEGER NOT NULL DEFAULT 0,
    weekly_enabled     INTEGER NOT NULL DEFAULT 0,
    send_time          TEXT    NOT NULL DEFAULT '18:00',
    mailjet_api_key    TEXT    NOT NULL DEFAULT '',
    mailjet_secret_key TEXT    NOT NULL DEFAULT '',
    resend_api_key     TEXT    NOT NULL DEFAULT '',
    send_provider      TEXT    NOT NULL DEFAULT 'resend',
    updated_at         REAL    NOT NULL DEFAULT 0
);

-- Per-channel signal parser configuration
CREATE TABLE IF NOT EXISTS channel_parser_config (
    channel_name            TEXT PRIMARY KEY,
    parser_format           TEXT NOT NULL DEFAULT 'auto',
    signal_prefix           TEXT NOT NULL DEFAULT '',
    instant_entry_enabled   INTEGER NOT NULL DEFAULT 0,
    enabled                 INTEGER NOT NULL DEFAULT 1,
    notes                   TEXT NOT NULL DEFAULT '',
    created_at              REAL NOT NULL DEFAULT 0,
    updated_at              REAL NOT NULL DEFAULT 0
);

-- Messages that did not match any configured parser
CREATE TABLE IF NOT EXISTS channel_unrecognised_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name    TEXT NOT NULL,
    tg_message_id   TEXT NOT NULL UNIQUE,
    raw_text        TEXT NOT NULL,
    received_at     REAL NOT NULL,
    claude_analysis TEXT,
    resolution      TEXT,
    resolved_at     REAL,
    status          TEXT NOT NULL DEFAULT 'pending'
);

-- AI fallback extractions (deterministic parser missed the message) pending
-- human review in Telegram > Reader Logic > AI tab. Approving one triggers
-- automatic regex-rule generation (see ai_rule_generator.py) so future
-- messages of the same shape are parsed deterministically, no AI call.
CREATE TABLE IF NOT EXISTS ai_recovered_signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_message_id   TEXT NOT NULL UNIQUE,
    channel_name    TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    direction       TEXT,
    entry_low       REAL,
    entry_high      REAL,
    stop_loss       REAL,
    tp1 REAL, tp2 REAL, tp3 REAL, tp4 REAL, tp5 REAL, tp6 REAL, tp7 REAL, tp8 REAL,
    confidence      REAL NOT NULL DEFAULT 0,
    reasoning       TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    approved        INTEGER NOT NULL DEFAULT 0,
    approved_at     REAL,
    rule_generated  INTEGER NOT NULL DEFAULT 0,
    rule_id         INTEGER,
    rule_gen_note   TEXT NOT NULL DEFAULT '',
    message_type    TEXT NOT NULL DEFAULT 'signal',
    new_stop_loss   REAL
);

-- One row per tg_message_id ever actioned by an SL-adjustment (either the
-- AI-fallback first pass or a matched ai_derived_sl_adjust learned rule) —
-- the dedup guard for SimulationEngine._apply_sl_adjustment(). Without this,
-- a message stays in the Telegram reader's buffer (get_buffer_messages) for
-- many scan cycles after being handled, and a broad learned-rule gate would
-- keep re-matching and re-firing on it every ~1s cycle indefinitely (found
-- live 2026-07-08: a single approved "adjust sl" rule with an unanchored
-- gate re-fired on the same message roughly once a minute for over half an
-- hour, spamming a Telegram alert each time even though the target SL never
-- changed). Entry signals don't need this separately since vantage_tg_signals
-- already dedupes them; SL-adjustments have no equivalent table of their own.
CREATE TABLE IF NOT EXISTS sl_adjustment_applied (
    tg_message_id TEXT PRIMARY KEY,
    channel_name  TEXT NOT NULL,
    new_stop_loss REAL,
    applied_at    REAL NOT NULL
);

-- One row per (tg_message_id, text) already put through the AI signal
-- fallback (SimulationEngine._try_ai_signal_fallback) — the dedup guard that
-- was missing entirely until 2026-07-08. Same root problem as
-- sl_adjustment_applied above: the Telegram reader's message buffer
-- (get_buffer_messages) holds recent messages regardless of processing
-- status, and this fallback is reached on every ~1s scan cycle for any
-- message still failing deterministic parsing. Without a claim here, a
-- single piece of channel chatter that was neither a signal nor an
-- SL-adjustment got reclassified by a live paid AI call every cycle,
-- indefinitely — confirmed live via a temporary caller-debug patch showing
-- ai_signal_extractor._classify firing continuously every ~2s with zero
-- corresponding Telegram activity. Keyed on a hash of the text (not just
-- tg_message_id) so a genuine edit still gets a fresh classification.
CREATE TABLE IF NOT EXISTS ai_fallback_checked (
    tg_message_id TEXT NOT NULL,
    text_hash     TEXT NOT NULL,
    checked_at    REAL NOT NULL,
    PRIMARY KEY (tg_message_id, text_hash)
);

-- Learned rules stored from user resolutions
CREATE TABLE IF NOT EXISTS channel_learned_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name    TEXT NOT NULL,
    rule_type       TEXT NOT NULL DEFAULT 'ignore_pattern',
    pattern         TEXT NOT NULL DEFAULT '',
    action          TEXT NOT NULL DEFAULT 'ignore',
    notes           TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    source_msg_id   TEXT
);

CREATE TABLE IF NOT EXISTS channel_performance (
    source          TEXT PRIMARY KEY,
    lot_mult        REAL NOT NULL DEFAULT 1.0,
    win_rate        REAL NOT NULL DEFAULT 0.0,
    sample_n        INTEGER NOT NULL DEFAULT 0,
    net_pnl         REAL NOT NULL DEFAULT 0.0,
    paused          INTEGER NOT NULL DEFAULT 0,
    manual_override INTEGER NOT NULL DEFAULT 0,
    updated_at      REAL NOT NULL DEFAULT 0
);
"""


def _apply_schema() -> None:
    with db() as conn:
        conn.executescript(_SCHEMA)
        # Migrations for existing databases (idempotent)
        for stmt in [
            "ALTER TABLE vantage_tg_signals ADD COLUMN group_name TEXT",
            "ALTER TABLE vantage_risk_settings ADD COLUMN profit_close_usd REAL NOT NULL DEFAULT 0.0",
            "ALTER TABLE mt5_credentials ADD COLUMN live_login INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE mt5_credentials ADD COLUMN live_password_enc TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE mt5_credentials ADD COLUMN live_server TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE mt5_credentials ADD COLUMN live_terminal_path TEXT",
            "ALTER TABLE email_config ADD COLUMN mailjet_api_key TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE email_config ADD COLUMN mailjet_secret_key TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE email_config ADD COLUMN resend_api_key TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE vantage_signals ADD COLUMN tp6 REAL",
            "ALTER TABLE vantage_signals ADD COLUMN tp7 REAL",
            "ALTER TABLE vantage_signals ADD COLUMN tp8 REAL",
            "ALTER TABLE vantage_simulated_trades ADD COLUMN tp6 REAL",
            "ALTER TABLE vantage_simulated_trades ADD COLUMN tp7 REAL",
            "ALTER TABLE vantage_simulated_trades ADD COLUMN tp8 REAL",
            "ALTER TABLE vantage_tg_signals ADD COLUMN tp6 REAL",
            "ALTER TABLE vantage_tg_signals ADD COLUMN tp7 REAL",
            "ALTER TABLE vantage_tg_signals ADD COLUMN tp8 REAL",
            "ALTER TABLE vantage_risk_settings ADD COLUMN display_strategy_id TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE vantage_risk_settings ADD COLUMN dpm_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN dpm_be_trigger_usd REAL NOT NULL DEFAULT 5.0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN dpm_trail_distance REAL NOT NULL DEFAULT 8.0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN dpm_tp1_partial_pct REAL NOT NULL DEFAULT 50.0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_start_time TEXT NOT NULL DEFAULT '22:00'",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_end_time TEXT NOT NULL DEFAULT '07:00'",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_strategy TEXT NOT NULL DEFAULT 'conservative'",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_date_from TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_date_to TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ooh_date_active INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN immediate_market_entry INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN exclude_high_risk INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE dpm_trade_performance ADD COLUMN tg_source TEXT",
            "ALTER TABLE email_config ADD COLUMN send_provider TEXT NOT NULL DEFAULT 'resend'",
            "ALTER TABLE vantage_risk_settings ADD COLUMN risk_governor_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_simulated_trades ADD COLUMN max_tp_hit TEXT",
            "ALTER TABLE vantage_risk_settings ADD COLUMN accept_tg_signals INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN sg_live_execution INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN bo_live_execution INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN unattended_mode INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN session_asia_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN session_london_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN session_ny_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN circuit_breaker_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN circuit_breaker_losses INTEGER NOT NULL DEFAULT 3",
            "ALTER TABLE vantage_risk_settings ADD COLUMN circuit_breaker_cooldown_mins INTEGER NOT NULL DEFAULT 60",
            "ALTER TABLE vantage_risk_settings ADD COLUMN circuit_breaker_active_until REAL NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN circuit_breaker_consec_losses INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN trail_stop_sl_pts REAL NOT NULL DEFAULT 5.0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN sg_claude_eval_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN bo_claude_eval_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE vantage_risk_settings ADD COLUMN atr_collapse_threshold REAL NOT NULL DEFAULT 0.65",
            "ALTER TABLE vantage_risk_settings ADD COLUMN kelly_sizing_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vantage_risk_settings ADD COLUMN gdc_live_execution INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE channel_performance ADD COLUMN strategy_override TEXT",
            "ALTER TABLE channel_performance ADD COLUMN auto_strategy INTEGER NOT NULL DEFAULT 0",
            """CREATE TABLE IF NOT EXISTS channel_strategy_rec (
                source     TEXT PRIMARY KEY,
                strategy   TEXT NOT NULL DEFAULT 'conservative',
                reasoning  TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.0,
                updated_at REAL NOT NULL DEFAULT 0
            )""",
            # 'python' (default, existing behaviour) or 'ea' — set when open_trade()
            # hands a trade's SL/TP/partial-close management off to the local MQL5
            # EA over the ea_bridge socket instead of managing it in _monitor_loop.
            # Flipped back to 'python' by the EA-heartbeat-timeout fallback if the
            # EA goes silent, so the trade is never left with no manager at all.
            "ALTER TABLE vantage_simulated_trades ADD COLUMN managed_by TEXT NOT NULL DEFAULT 'python'",
            "ALTER TABLE vantage_risk_settings ADD COLUMN ea_bridge_enabled INTEGER NOT NULL DEFAULT 0",
            # Shared by both Bounce and Breakout generators — off by default (a
            # measured toxic-hour block was previously always-on per engine via
            # each one's own adaptive_params "hour_filter_enabled", with no user
            # facing toggle). When on, a blocked hour no longer suppresses signal
            # generation at all (the model still needs fresh data from those
            # hours to keep validating the measurement) — it only blocks
            # _execute_live() from placing the real MT5 order, exactly like the
            # existing daily-loss circuit breaker already does.
            "ALTER TABLE vantage_risk_settings ADD COLUMN hour_blocklist_enabled INTEGER NOT NULL DEFAULT 0",
            # 'signal' (default, a new entry) or 'sl_adjustment' — a follow-up
            # instruction to move an existing trade's SL, e.g. "Adjust SL to
            # 4060", recognised by the same AI fallback but reviewed/approved
            # and turned into a rule separately since it drives a different
            # live action (modify an open trade, not open a new one).
            "ALTER TABLE ai_recovered_signals ADD COLUMN message_type TEXT NOT NULL DEFAULT 'signal'",
            "ALTER TABLE ai_recovered_signals ADD COLUMN new_stop_loss REAL",
            # Morning ORB (opening-range breakout) report — a fixed 08:15
            # Europe/London send, independent of the daily/weekly summary's
            # configurable send_time, since it's tied to the London session
            # open rather than an arbitrary time of day. Defaults on: this is
            # an explicit user request, not an opt-in feature like the other
            # email reports above.
            "ALTER TABLE email_config ADD COLUMN orb_report_enabled INTEGER NOT NULL DEFAULT 1",
            # ORB/IVB Report tab's auto-execute toggle — places a real trade
            # every morning off the London-open reload-zone setup with no
            # further management (STRATEGY_ORB_FIXED). Defaults OFF unlike the
            # informational email above — this one moves real money/demo
            # positions unattended, so it must be an explicit opt-in.
            "ALTER TABLE vantage_risk_settings ADD COLUMN orb_auto_execute_enabled INTEGER NOT NULL DEFAULT 0",
            # ORB/IVB Report's lot size — shared by the manual Execute button
            # and the auto-execute scheduler, so a fixed size set once applies
            # to both. 0 = auto-size from Risk % and stop distance, matching
            # the Market Order tab's convention.
            "ALTER TABLE vantage_risk_settings ADD COLUMN orb_lot_size REAL NOT NULL DEFAULT 0",
            # Centralized signal generation — when on and this VPS is the
            # active trader, the VPS stops running its own Breakout/TestSignal
            # /GDCopy/GD2-GD-VIP analysis entirely and only executes trades
            # forwarded from the Mac (see should_generate_signals_here()).
            # Defaults off: changes which node's signals actually trade and
            # removes the VPS's ability to self-generate if the Mac drops.
            "ALTER TABLE vantage_risk_settings ADD COLUMN centralized_signal_gen_enabled INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass  # column already exists
        # Enable instant_entry for any GD2 channel configs that were bootstrapped
        # before the GD2 IME support was added (they defaulted to 0).
        conn.execute(
            "UPDATE channel_parser_config "
            "SET instant_entry_enabled=1 "
            "WHERE parser_format='gd2' AND instant_entry_enabled=0"
        )
        # Strip legacy "instant:" prefix from tg_source in all trade tables
        conn.execute(
            "UPDATE vantage_simulated_trades "
            "SET tg_source = SUBSTR(tg_source, 9) "
            "WHERE tg_source LIKE 'instant:%'"
        )
        conn.execute(
            "UPDATE vantage_signals "
            "SET source_name = SUBSTR(source_name, 9) "
            "WHERE source_name LIKE 'instant:%'"
        )
        # Backfill tg_source into dpm_trade_performance from the trade record
        conn.execute(
            "UPDATE dpm_trade_performance "
            "SET tg_source = ("
            "    SELECT tg_source FROM vantage_simulated_trades t "
            "    WHERE t.trade_id = dpm_trade_performance.trade_id"
            ") WHERE tg_source IS NULL OR tg_source LIKE 'instant:%'"
        )
        # singleton rows
        from forex_trader.config import get as cfg_get
        starting_balance = cfg_get("starting_balance", 1000.0)
        mt5_login = cfg_get("mt5_login", 0)
        mt5_server = cfg_get("mt5_server", "")
        conn.execute(
            "INSERT OR IGNORE INTO mt5_credentials(id,login,server) VALUES(1,?,?)",
            (mt5_login, mt5_server),
        )
        conn.execute(
            "INSERT OR IGNORE INTO vantage_simulation_account(id,balance,reset_at) VALUES(1,?,?)",
            (starting_balance, time.time()),
        )
        conn.execute("INSERT OR IGNORE INTO telegram_config(id) VALUES(1)")
        conn.execute("INSERT OR IGNORE INTO vantage_risk_settings(id) VALUES(1)")
        conn.execute("INSERT OR IGNORE INTO vantage_fee_settings(id) VALUES(1)")
        conn.execute("INSERT OR IGNORE INTO email_config(id) VALUES(1)")


# ── CRUD helpers ──────────────────────────────────────────────────────────────

_rs_cache:    Optional[dict] = None
_rs_cache_ts: float = 0.0
_RS_CACHE_TTL = 10.0  # seconds — risk settings change only on user edit


def get_risk_settings() -> dict:
    global _rs_cache, _rs_cache_ts
    now = time.time()
    if _rs_cache is not None and (now - _rs_cache_ts) < _RS_CACHE_TTL:
        return _rs_cache
    with db() as conn:
        result = row_to_dict(conn.execute("SELECT * FROM vantage_risk_settings WHERE id=1").fetchone())
    _rs_cache    = result
    _rs_cache_ts = now
    return result


_applying_sync_settings = False  # re-entrancy guard — see update_risk_settings


def update_risk_settings(updates: dict, _from_sync: bool = False) -> dict:
    """Update risk settings and, for a normal (non-sync-originated) edit,
    forward the change over the Local/Remote sync channel if one is active.

    _from_sync=True is used only by the two call sites that are themselves
    APPLYING a value that arrived over the sync channel (the Mac's
    settings-mirror on receipt of MSG_SETTINGS_STATE, and the VPS applying a
    Mac's MSG_SETTINGS_PROPOSE) — without this guard, applying an incoming
    sync value would immediately re-forward it back out, an infinite
    propose/confirm ping-pong between the two nodes.
    """
    global _rs_cache, _rs_cache_ts, _applying_sync_settings
    if not updates:
        return get_risk_settings()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    with db() as conn:
        conn.execute(f"UPDATE vantage_risk_settings SET {set_clause} WHERE id=1",
                     list(updates.values()))
    _rs_cache    = None   # invalidate so next read hits the DB
    _rs_cache_ts = 0.0
    result = get_risk_settings()

    if not _from_sync and not _applying_sync_settings:
        _applying_sync_settings = True
        try:
            _forward_settings_over_sync(updates)
        finally:
            _applying_sync_settings = False
    return result


def _schedule_coro(coro) -> None:
    """Schedule a coroutine regardless of which thread calls this — the
    main event-loop thread (asyncio.ensure_future works directly) or the
    dedicated DB worker thread / any other thread (needs
    run_coroutine_threadsafe targeting the captured main loop instead,
    since ensure_future only works on the thread actually running that
    loop). See set_main_event_loop's docstring above for why this exists."""
    try:
        asyncio.get_running_loop()
        asyncio.ensure_future(coro)
    except RuntimeError:
        if _main_loop is not None:
            asyncio.run_coroutine_threadsafe(coro, _main_loop)
        else:
            coro.close()  # avoid a dangling "never awaited" coroutine


def _forward_settings_over_sync(updates: dict) -> None:
    """Send a locally-made settings change to the paired node, whichever
    role this process has. No-op (and near-zero cost) if sync isn't
    configured — both get_instance() calls return None until sync.server
    .init()/sync.client.get_instance() have actually been used."""
    try:
        from forex_trader.sync import client as _sync_cli_mod
        cli = _sync_cli_mod.get_instance()
        if cli is not None:
            # propose_settings() queues into cli._pending_settings and only
            # attempts to send if currently connected — calling it here even
            # while disconnected is what makes the change durable across the
            # frequent reconnects this link sees, instead of silently
            # dropping it when conn_state isn't "connected" at this instant.
            _schedule_coro(cli.propose_settings(updates))
            return
    except Exception as e:
        log.debug("[Sync] settings forward (client) failed: %s", e)

    try:
        from forex_trader.sync import server as _sync_srv_mod
        srv = _sync_srv_mod.get_instance()
        if srv is not None:
            _schedule_coro(srv.broadcast_settings())
    except Exception as e:
        log.debug("[Sync] settings forward (server) failed: %s", e)


def is_session_allowed(rs: Optional[dict] = None) -> tuple[bool, str]:
    """Return (allowed, session_name) based on the user's Trading Markets selection.

    Session mapping:
      "asian"   → Asia button (21:00–07:00 UTC)
      "london"  → London button (07:00–12:00 UTC, pre-overlap)
      "overlap" → London OR New York button (12:00–16:00 UTC)
      "ny"      → New York button (16:00–21:00 UTC, post-overlap)
    """
    from forex_trader.core.dpm_engine import detect_session, is_weekly_market_closed  # local to avoid circular import
    if is_weekly_market_closed():
        return False, "closed"
    if rs is None:
        rs = get_risk_settings()
    enabled: set[str] = set()
    if rs.get("session_asia_enabled", 1):
        enabled.add("asian")
    if rs.get("session_london_enabled", 1):
        enabled.add("london")
        enabled.add("overlap")
    if rs.get("session_ny_enabled", 1):
        enabled.add("ny")
        enabled.add("overlap")
    session = detect_session()
    return session in enabled, session


def get_fee_settings() -> dict:
    with db() as conn:
        return row_to_dict(conn.execute("SELECT * FROM vantage_fee_settings WHERE id=1").fetchone())


def update_fee_settings(updates: dict) -> dict:
    if not updates:
        return get_fee_settings()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    with db() as conn:
        conn.execute(f"UPDATE vantage_fee_settings SET {set_clause} WHERE id=1",
                     list(updates.values()))
    return get_fee_settings()


def get_custom_strategies() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM custom_strategies ORDER BY created_at"
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def save_custom_strategy(s: dict) -> None:
    with db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO custom_strategies
               (id, name, description, base_strategy, rules_json, created_at)
               VALUES (:id, :name, :description, :base_strategy, :rules_json, :created_at)""",
            s,
        )


def delete_custom_strategy(strategy_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM custom_strategies WHERE id=?", (strategy_id,))


def get_telegram_config() -> dict:
    with db() as conn:
        return row_to_dict(conn.execute("SELECT * FROM telegram_config WHERE id=1").fetchone())


def save_telegram_config(bot_token: str, chat_id: str, enabled: bool) -> None:
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO telegram_config (id,bot_token_enc,chat_id,enabled,updated_at)"
            " VALUES (1,?,?,?,?)",
            (bot_token, chat_id, int(enabled), time.time()),
        )


def log_telegram_event(event_type: str, trade_id: Optional[str], status: str, detail: Optional[str]) -> None:
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO vantage_telegram_log (ts,event_type,trade_id,status,detail) VALUES (?,?,?,?,?)",
                (time.time(), event_type, trade_id, status, detail),
            )
    except Exception as e:
        log.debug("telegram log write failed: %s", e)


def save_telegram_reader_event(event_type: str, status: str, message: str, details: Optional[dict] = None) -> None:
    from datetime import datetime, timezone
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO telegram_reader_events (timestamp,event_type,status,message,details_json)"
                " VALUES (?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), event_type, status, message,
                 json.dumps(details) if details else None),
            )
    except Exception as e:
        log.debug("reader event write failed: %s", e)


def store_telegram_message(msg: dict) -> None:
    try:
        with db() as conn:
            # received_at is supposed to be the moment this message was first
            # seen — a real latency signal. But every reconnect re-backfills
            # the last 20 messages per channel (TelegramReader._backfill) and
            # calls this same function again for messages already stored by
            # the live handler; INSERT OR REPLACE was unconditionally
            # overwriting received_at with the backfill's "now", silently
            # inflating it by however long the reconnect took (confirmed
            # live 2026-07-10 — ~20+ min gaps traced to restart timing, not
            # actual signal latency). Preserve the first-seen value if a row
            # already exists; still refresh every other field (text edits,
            # sender resolution, etc. should still take the latest).
            existing = conn.execute(
                "SELECT received_at FROM telegram_messages WHERE telegram_message_id=? AND group_id=?",
                (str(msg["id"]), str(msg["group_id"])),
            ).fetchone()
            received_at = existing[0] if existing and existing[0] else msg.get("received_at")
            raw_json_msg = dict(msg)
            raw_json_msg["received_at"] = received_at
            conn.execute(
                """INSERT OR REPLACE INTO telegram_messages
                   (telegram_message_id,group_id,group_name,sender_id,sender_name,
                    timestamp,received_at,text,raw_text,has_media,media_type,
                    reply_to_message_id,forwarded,raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(msg["id"]), str(msg["group_id"]), msg.get("group_name", ""),
                    str(msg.get("sender_id") or ""), msg.get("sender_name") or "",
                    msg.get("timestamp"), received_at,
                    msg.get("text") or "", msg.get("raw_text") or "",
                    1 if msg.get("has_media") else 0, msg.get("media_type") or "none",
                    str(msg["reply_to_message_id"]) if msg.get("reply_to_message_id") else None,
                    1 if msg.get("forwarded") else 0,
                    json.dumps(raw_json_msg),
                ),
            )
    except Exception as e:
        log.error("message store failed: %s", e)


def get_stored_messages(limit: int = 100, offset: int = 0, group_id: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if group_id:
            rows = conn.execute(
                "SELECT * FROM telegram_messages WHERE group_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (str(group_id), min(limit, 500), offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM telegram_messages ORDER BY id DESC LIMIT ? OFFSET ?",
                (min(limit, 500), offset),
            ).fetchall()
    return [dict(r) for r in rows]


def save_commentary(commentary: dict, trade_id: Optional[str], signal_id: Optional[str]) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO vantage_claude_commentary (ts,event_type,trade_id,signal_id,payload)"
            " VALUES (?,?,?,?,?)",
            (time.time(), commentary.get("commentary_type", ""), trade_id, signal_id,
             json.dumps(commentary)),
        )


def get_email_config() -> dict:
    with db() as conn:
        return row_to_dict(conn.execute("SELECT * FROM email_config WHERE id=1").fetchone())


def create_ladder_leg(trade_id: str, tier: int, tp_num: int, tp_price: float,
                       lots: float, mt5_ticket: Optional[int],
                       entry_price: Optional[float] = None) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO vantage_ladder_legs (trade_id,tier,tp_num,tp_price,lots,mt5_ticket,"
            "entry_price) VALUES (?,?,?,?,?,?,?)",
            (trade_id, tier, tp_num, tp_price, lots, mt5_ticket, entry_price),
        )
        return cur.lastrowid


def get_ladder_legs(trade_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM vantage_ladder_legs WHERE trade_id=? ORDER BY tier", (trade_id,)
        ).fetchall()
    return [row_to_dict(r) for r in rows]


def close_ladder_leg(leg_id: int, close_price: float, pnl: float, status: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE vantage_ladder_legs SET status=?,close_price=?,close_time=?,pnl=? WHERE id=?",
            (status, close_price, time.time(), pnl, leg_id),
        )


def save_max_tp_hit(trade_id: str, value: str) -> None:
    """Persist the max TP level reached during the trade's own open->close window."""
    with db() as conn:
        conn.execute(
            "UPDATE vantage_simulated_trades SET max_tp_hit=? WHERE trade_id=?",
            (value, trade_id),
        )


def get_trades_with_max_tp_set() -> list[dict]:
    """Return closed trades that already have max_tp_hit computed.

    Used by the one-off backfill (engine.py's _backfill_max_tp_hit_corrected,
    2026-07-18) that recomputes every existing value against the corrected
    open_time->close_time window, replacing values computed under the old
    close_time+30min window that could attribute post-close price action to
    a trade that had already closed."""
    with db() as conn:
        rows = conn.execute(
            "SELECT t.trade_id, t.direction, t.open_time, t.close_time, "
            "t.max_tp_hit AS old_hit, t.strategy, t.tg_source, t.mt5_ticket, t.net_pnl, "
            "t.tp1, t.tp2, t.tp3, t.tp4, t.tp5, t.tp6, t.tp7, t.tp8, "
            "s.tp1 AS sig_tp1, s.tp2 AS sig_tp2, s.tp3 AS sig_tp3, "
            "s.tp4 AS sig_tp4, s.tp5 AS sig_tp5, s.tp6 AS sig_tp6, "
            "s.tp7 AS sig_tp7, s.tp8 AS sig_tp8 "
            "FROM vantage_simulated_trades t "
            "LEFT JOIN vantage_signals s ON s.signal_id = t.signal_id "
            "WHERE t.status='closed' AND t.max_tp_hit IS NOT NULL "
            "  AND t.open_time IS NOT NULL AND t.close_time > 0"
        ).fetchall()
    return [dict(r) for r in rows]


def get_max_tp_map_by_ticket() -> dict[str, str]:
    """Return {mt5_ticket_str: max_tp_hit} for all trades that have been computed."""
    with db() as conn:
        rows = conn.execute(
            "SELECT mt5_ticket, max_tp_hit FROM vantage_simulated_trades "
            "WHERE mt5_ticket IS NOT NULL AND max_tp_hit IS NOT NULL"
        ).fetchall()
    return {str(r[0]): r[1] for r in rows}


def get_rr_map_by_ticket() -> dict[str, float]:
    """Return {mt5_ticket_str: reward:risk ratio} computed from each trade's
    own entry_price/stop_loss/tp1 — the actual fill and the actual levels
    that trade was managed under (not the raw Telegram signal's, which a
    self-managed strategy like Conservative may have overridden entirely).
    Available immediately at close, unlike max_tp_hit which needs the 30-min
    post-close window — no async job involved, just excluded here whenever
    any of the three inputs is missing or entry equals stop (zero risk,
    ratio undefined)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT mt5_ticket, entry_price, stop_loss, tp1 FROM vantage_simulated_trades "
            "WHERE mt5_ticket IS NOT NULL AND entry_price IS NOT NULL "
            "AND stop_loss IS NOT NULL AND tp1 IS NOT NULL AND stop_loss != entry_price"
        ).fetchall()
    result: dict[str, float] = {}
    for mt5_ticket, entry_price, stop_loss, tp1 in rows:
        risk = abs(float(entry_price) - float(stop_loss))
        if risk <= 0:
            continue
        result[str(mt5_ticket)] = abs(float(tp1) - float(entry_price)) / risk
    return result


def get_trades_pending_max_tp(cutoff_ts: float) -> list[dict]:
    """Return closed trades whose 30-min window has elapsed but max_tp_hit is not set.

    Joins vantage_signals to return the original signal's TP ladder (sig_tp1..sig_tp8)
    alongside the trade's own TPs.  The caller should prefer signal TPs so the Max TP
    column reflects how far price ran relative to the original signal levels, regardless
    of which strategy SL/TP the trade was closed under.

    Also returns strategy/tg_source/mt5_ticket/net_pnl — not used for the
    max_tp computation itself, but needed by the caller's follow-up
    push_trade_closed() call so the consolidated-ledger upsert (the one that
    finally lets the OTHER node's History view show this trade's Max TP Hit)
    doesn't have to clobber those fields with placeholder values.
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT t.trade_id, t.direction, t.open_time, t.close_time, "
            "t.strategy, t.tg_source, t.mt5_ticket, t.net_pnl, "
            "t.tp1, t.tp2, t.tp3, t.tp4, t.tp5, t.tp6, t.tp7, t.tp8, "
            "s.tp1 AS sig_tp1, s.tp2 AS sig_tp2, s.tp3 AS sig_tp3, "
            "s.tp4 AS sig_tp4, s.tp5 AS sig_tp5, s.tp6 AS sig_tp6, "
            "s.tp7 AS sig_tp7, s.tp8 AS sig_tp8 "
            "FROM vantage_simulated_trades t "
            "LEFT JOIN vantage_signals s ON s.signal_id = t.signal_id "
            "WHERE t.status='closed' AND t.max_tp_hit IS NULL "
            "  AND t.close_time > 0 AND t.close_time <= ? "
            "  AND (t.tp1 IS NOT NULL OR s.tp1 IS NOT NULL)",
            (cutoff_ts,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Performance analytics (heat map + channel scorecard) ──────────────────────

def _session_for_hour(h: int) -> str:
    """Map a UTC hour to a trading session (mirrors dpm_engine.detect_session)."""
    london = 7 <= h < 16
    ny     = 12 <= h < 21
    if london and ny:
        return "overlap"
    if london:
        return "london"
    if ny:
        return "ny"
    return "asian"


def _trade_pts(direction: str, entry: float, close: float) -> float:
    """Signed points gained on a trade (positive = profit)."""
    if not entry or not close:
        return 0.0
    return (close - entry) if (direction or "").upper() == "BUY" else (entry - close)


def get_hourly_pnl_grid(days: int = 90) -> dict:
    """Return {(weekday, hour): {'pnl': total, 'n': count, 'avg': avg}} from closed
    trades over the last `days`, bucketed by UTC weekday (0=Mon) and hour.

    Merges in the consolidated ledger (see consolidated_trades) as a fallback
    for trades the OTHER paired node closed and has no local
    vantage_simulated_trades row for — same cross-node gap/fallback pattern
    already used by History's Trade History tab (get_consolidated_extra_maps).
    Deduped by trade_id since every locally-closed trade already has its own
    row in this node's own local copy of consolidated_trades too."""
    import time as _t
    from datetime import datetime as _dt, timezone as _tz
    _ensure_sync_tables()
    cutoff = _t.time() - days * 86400
    grid: dict[tuple, dict] = {}
    local_ids: set[str] = set()
    with db() as conn:
        rows = conn.execute(
            "SELECT close_time, net_pnl, trade_id FROM vantage_simulated_trades "
            "WHERE status='closed' AND close_time >= ?",
            (cutoff,),
        ).fetchall()
        ledger_rows = conn.execute(
            "SELECT close_time, pnl_dollars, trade_id FROM consolidated_trades "
            "WHERE close_time >= ?", (cutoff,),
        ).fetchall()
    for ct, pnl, tid in rows:
        local_ids.add(tid)
        if not ct:
            continue
        d = _dt.fromtimestamp(float(ct), tz=_tz.utc)
        key = (d.weekday(), d.hour)
        cell = grid.setdefault(key, {"pnl": 0.0, "n": 0})
        cell["pnl"] += float(pnl or 0)
        cell["n"]   += 1
    for ct, pnl, tid in ledger_rows:
        if tid in local_ids or not ct:
            continue
        d = _dt.fromtimestamp(float(ct), tz=_tz.utc)
        key = (d.weekday(), d.hour)
        cell = grid.setdefault(key, {"pnl": 0.0, "n": 0})
        cell["pnl"] += float(pnl or 0)
        cell["n"]   += 1
    for cell in grid.values():
        cell["avg"] = round(cell["pnl"] / cell["n"], 2) if cell["n"] else 0.0
    return grid


# Known Telegram numeric group IDs → display names.
# These appear when a trade's tg_source was stored as the raw group_id
# rather than the resolved channel name (older instant-entry code path).
_TG_GROUP_ID_MAP: dict[str, str] = {
    "1608388054": "Gold Diggers VIP",
    "2616846888": "GOLD DIGGERS 2.0 ⚡️",
}


def _normalise_tg_source(src: str) -> str:
    """Map raw numeric Telegram group IDs to human-readable channel names."""
    return _TG_GROUP_ID_MAP.get(str(src).strip(), src) if src else src


def get_channel_scorecard(days: int = 30) -> list[dict]:
    """Per signal-source performance over the last `days`, sorted by net P&L desc.
    Each row: source, trades, wins, losses, win_rate, avg_pts, payoff_rr,
    net_pnl, and a per-session {london/ny/overlap/asian: net_pnl} split.

    Merges in the consolidated ledger as a fallback for trades the OTHER
    paired node closed (e.g. GD Copy Engine's live-executed trades, which
    live in gd_copy_signal's own DB and never get a vantage_simulated_trades
    row at all — see gd_copy_signal/engine.py's _reconcile_live_signal,
    which pushes to the ledger via push_trade_closed regardless of which
    node ran the trade). Ledger rows have no entry_price/close_price, so
    their points-based contribution (avg_pts/payoff_rr) is 0 — win/loss
    counts and net_pnl, the primary numbers here, are unaffected."""
    import time as _t
    from datetime import datetime as _dt, timezone as _tz
    _ensure_sync_tables()
    cutoff = _t.time() - days * 86400
    with db() as conn:
        rows = conn.execute(
            "SELECT tg_source, direction, entry_price, close_price, net_pnl, close_time, trade_id "
            "FROM vantage_simulated_trades "
            "WHERE status='closed' AND mt5_ticket IS NOT NULL AND close_time >= ?",
            (cutoff,),
        ).fetchall()
        ledger_rows = conn.execute(
            "SELECT tg_source, direction, pnl_dollars, close_time, trade_id "
            "FROM consolidated_trades WHERE mt5_ticket IS NOT NULL AND close_time >= ?",
            (cutoff,),
        ).fetchall()

    local_ids = {r[6] for r in rows}
    agg: dict[str, dict] = {}
    for tg_source, direction, entry, close, pnl, ct, _tid in rows:
        src = _normalise_tg_source(tg_source or "Manual Signal")
        a = agg.setdefault(src, {
            "source": src, "trades": 0, "wins": 0, "losses": 0,
            "net_pnl": 0.0, "win_pts": [], "loss_pts": [], "all_pts": [],
            "sessions": {"london": 0.0, "ny": 0.0, "overlap": 0.0, "asian": 0.0},
        })
        pnl = float(pnl or 0)
        pts = _trade_pts(direction, float(entry or 0), float(close or 0))
        a["trades"]  += 1
        a["net_pnl"] += pnl
        a["all_pts"].append(pts)
        if pnl > 0:
            a["wins"] += 1
            a["win_pts"].append(pts)
        elif pnl < 0:
            a["losses"] += 1
            a["loss_pts"].append(abs(pts))
        if ct:
            sess = _session_for_hour(_dt.fromtimestamp(float(ct), tz=_tz.utc).hour)
            a["sessions"][sess] += pnl

    for tg_source, direction, pnl, ct, tid in ledger_rows:
        if tid in local_ids:
            continue
        src = _normalise_tg_source(tg_source or "Manual Signal")
        a = agg.setdefault(src, {
            "source": src, "trades": 0, "wins": 0, "losses": 0,
            "net_pnl": 0.0, "win_pts": [], "loss_pts": [], "all_pts": [],
            "sessions": {"london": 0.0, "ny": 0.0, "overlap": 0.0, "asian": 0.0},
        })
        pnl = float(pnl or 0)
        a["trades"]  += 1
        a["net_pnl"] += pnl
        if pnl > 0:
            a["wins"] += 1
        elif pnl < 0:
            a["losses"] += 1
        if ct:
            sess = _session_for_hour(_dt.fromtimestamp(float(ct), tz=_tz.utc).hour)
            a["sessions"][sess] += pnl

    out = []
    for a in agg.values():
        decided = a["wins"] + a["losses"]
        wr  = (a["wins"] / decided * 100) if decided else 0.0
        avg_pts = (sum(a["all_pts"]) / len(a["all_pts"])) if a["all_pts"] else 0.0
        avg_win  = (sum(a["win_pts"]) / len(a["win_pts"])) if a["win_pts"] else 0.0
        avg_loss = (sum(a["loss_pts"]) / len(a["loss_pts"])) if a["loss_pts"] else 0.0
        payoff = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0
        out.append({
            "source": a["source"], "trades": a["trades"],
            "wins": a["wins"], "losses": a["losses"],
            "win_rate": round(wr, 1), "avg_pts": round(avg_pts, 2),
            "payoff_rr": payoff, "net_pnl": round(a["net_pnl"], 2),
            "sessions": {k: round(v, 2) for k, v in a["sessions"].items()},
        })
    out.sort(key=lambda r: r["net_pnl"], reverse=True)
    return out


# Adaptive lot multiplier thresholds (rolling profit factor over MIN_SAMPLE trades).
_CHANNEL_MIN_SAMPLE   = 8    # need this many decided trades before adapting
_CHANNEL_PAUSE_PF     = 0.0  # auto-pause disabled (set > 0 to re-enable)
# Sources that are never auto-paused — user controls them manually.
_CHANNEL_NO_AUTO_PAUSE = {"Signal Generator", "Bounce Generator", "manual_market"}


def _channel_profit_factor(r: dict) -> float:
    """Compute dollar profit factor from scorecard row.
    PF = (win_rate × payoff_rr) / (1 − win_rate/100)  [points-normalised approximation].
    Returns 0.0 when there is no loss history."""
    wr  = r["win_rate"] / 100.0
    rr  = r.get("payoff_rr", 0.0)
    if wr >= 1.0 or rr <= 0:
        return 0.0 if rr <= 0 else 99.0
    return round((wr * rr) / (1.0 - wr), 3)


def recompute_channel_performance(days: int = 30) -> list[str]:
    """Recompute per-channel lot multipliers and auto-pause flags from rolling
    `days` performance, and upsert into channel_performance. Rows with
    manual_override=1 keep their paused flag (set by the user) untouched.

    Returns a list of source names that were newly auto-paused this run,
    so callers can send a Telegram alert."""
    import time as _t
    scorecard = get_channel_scorecard(days)
    now = _t.time()
    newly_paused: list[str] = []
    with db() as conn:
        for r in scorecard:
            src = r["source"]
            n   = r["wins"] + r["losses"]
            pf  = _channel_profit_factor(r)
            wr  = r["win_rate"]

            if n < _CHANNEL_MIN_SAMPLE or src in _CHANNEL_NO_AUTO_PAUSE:
                lot_mult, auto_pause = 1.0, 0
            elif pf < _CHANNEL_PAUSE_PF:
                lot_mult, auto_pause = 0.5, 1
            elif wr < 55.0:
                lot_mult, auto_pause = 1.0, 0
            else:
                lot_mult, auto_pause = 1.3, 0

            row = conn.execute(
                "SELECT manual_override, paused FROM channel_performance WHERE source=?",
                (src,),
            ).fetchone()
            if row and row[0]:
                paused = row[1]  # user override always wins
            else:
                was_paused = bool(row[1]) if row else False
                paused = auto_pause
                if auto_pause and not was_paused:
                    newly_paused.append(src)

            conn.execute(
                "INSERT INTO channel_performance "
                "(source, lot_mult, win_rate, sample_n, net_pnl, paused, manual_override, updated_at) "
                "VALUES (?,?,?,?,?,?,COALESCE((SELECT manual_override FROM channel_performance WHERE source=?),0),?) "
                "ON CONFLICT(source) DO UPDATE SET "
                "  lot_mult=excluded.lot_mult, win_rate=excluded.win_rate, "
                "  sample_n=excluded.sample_n, net_pnl=excluded.net_pnl, "
                "  paused=?, updated_at=excluded.updated_at",
                (src, lot_mult, wr, n, r["net_pnl"], paused, src, now, paused),
            )
    return newly_paused


def get_channel_lot_mult(source: str) -> tuple[float, bool]:
    """Return (lot_multiplier, paused) for a signal source. Defaults (1.0, False)."""
    if not source:
        return 1.0, False
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT lot_mult, paused FROM channel_performance WHERE source=?",
                (source,),
            ).fetchone()
        if not row:
            return 1.0, False
        return float(row[0] or 1.0), bool(row[1])
    except Exception:
        return 1.0, False


_CHANNEL_TRUST_MIN_SAMPLES = 20   # minimum closed trades to consider a channel trusted
_CHANNEL_TRUST_MIN_WR      = 50.0 # minimum win-rate % (stored as 50.0 = 50%)

def get_channel_trust(source: str) -> bool:
    """Return True if a channel has a statistically proven, net-profitable track record.

    Trust criteria (must pass all three):
      - sample_n >= 20 (enough data to be meaningful)
      - win_rate >= 50% (more wins than losses, column stores 55.9 for 55.9%)
      - net_pnl > 0 (actually made money in our system)

    Checks both the raw channel name and the 'Telegram Auto (<name>)' variant
    that the auto-execution path uses when logging trades, since signals arrive
    under the channel name but executed trades may be stored under the prefixed form.
    """
    if not source:
        return False
    candidates = [source, f"Telegram Auto ({source})"]
    try:
        with db() as conn:
            for candidate in candidates:
                row = conn.execute(
                    "SELECT win_rate, sample_n, net_pnl FROM channel_performance WHERE source=?",
                    (candidate,),
                ).fetchone()
                if not row:
                    continue
                if (
                    (row[1] or 0) >= _CHANNEL_TRUST_MIN_SAMPLES
                    and (row[0] or 0.0) >= _CHANNEL_TRUST_MIN_WR
                    and (row[2] or 0.0) > 0
                ):
                    return True
    except Exception:
        pass
    return False


# Canonical channel names used in the Channel Strategy UI.
# Every variant maps to its canonical name so strategy overrides
# are stored and looked up consistently regardless of how a trade
# source was labelled by Telegram or legacy code.
CANONICAL_CHANNELS: dict[str, str] = {
    # Gold Diggers 2.0 variants
    "GOLD DIGGERS 2.0 ⚡️":           "Gold Diggers 2.0",
    "Telegram Auto (GOLD DIGGERS 2.0 ⚡️)": "Gold Diggers 2.0",
    "2616846888":                               "Gold Diggers 2.0",
    "Gold Diggers 2.0":                         "Gold Diggers 2.0",
    # Gold Diggers VIP variants
    "Gold Diggers VIP":                         "Gold Diggers VIP",
    "Telegram Auto (Gold Diggers VIP)":         "Gold Diggers VIP",
    "1608388054":                               "Gold Diggers VIP",
    # Signal generators
    "Signal Generator":                         "Bounce Engine",   # legacy tg_source
    "Bounce Generator":                         "Bounce Engine",
    "Bounce Engine":                            "Bounce Engine",
    "Breakout Engine":                          "Breakout Engine",
    # GD Copy engine
    "GD Copy Engine":                           "GD Copy Engine",
    "Gold Diggers VIP Copy":                    "GD Copy Engine",
}

# Display order for the Channel Strategy UI
CANONICAL_CHANNEL_ORDER = [
    "Gold Diggers 2.0",
    "Gold Diggers VIP",
    "GD Copy Engine",
    "Bounce Engine",
    "Breakout Engine",
]


def _canonical(source: str) -> str:
    """Return the canonical channel name for a raw tg_source / source string."""
    return CANONICAL_CHANNELS.get(source, source)


def get_channel_strategy_override(source: str):
    """Return the per-channel strategy override string, or None (inherit global).

    Returns 'auto' when auto-Claude mode is active, a strategy key when manually
    overridden, or None to fall back to the global Active Strategy setting.
    Looks up using the canonical channel name so all variants share one setting.
    """
    if not source:
        return None
    canon = _canonical(source)
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT strategy_override, auto_strategy FROM channel_performance WHERE source=?",
                (canon,),
            ).fetchone()
        if not row:
            return None
        if row[1]:      # auto_strategy flag set
            return "auto"
        return row[0]   # strategy_override TEXT (may be None)
    except Exception:
        return None


_applying_sync_channel_strategy = False  # re-entrancy guard — see update_risk_settings


def set_channel_strategy_override(
    source: str, strategy: str | None, auto: bool = False, _from_sync: bool = False,
) -> None:
    """Set per-channel strategy.  strategy=None + auto=False clears override (inherit global).

    _from_sync=True is used only when APPLYING a value that arrived over the
    Local/Remote sync channel — without this guard, applying an incoming
    sync value would immediately re-forward it back out, an infinite
    propose/confirm ping-pong between the two nodes (same pattern as
    update_risk_settings above)."""
    global _applying_sync_channel_strategy
    import time as _t
    canon = _canonical(source)
    with db() as conn:
        conn.execute(
            "INSERT INTO channel_performance (source, strategy_override, auto_strategy, updated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(source) DO UPDATE SET strategy_override=excluded.strategy_override, "
            "  auto_strategy=excluded.auto_strategy, updated_at=excluded.updated_at",
            (canon, strategy, 1 if auto else 0, _t.time()),
        )
    if not _from_sync and not _applying_sync_channel_strategy:
        _applying_sync_channel_strategy = True
        try:
            _forward_channel_strategy_over_sync(canon, strategy, auto)
        finally:
            _applying_sync_channel_strategy = False


def get_all_channel_strategy_overrides() -> dict[str, dict]:
    """Lightweight {canonical_source: {strategy, auto}} snapshot for sync —
    just the override fields, not the per-node performance stats that
    get_all_channel_strategy_settings() also returns."""
    result = {ch: {"strategy": None, "auto": False} for ch in CANONICAL_CHANNEL_ORDER}
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT source, strategy_override, auto_strategy FROM channel_performance"
            ).fetchall()
        for source, strategy, auto in rows:
            if source in result:  # canonical rows only — variants don't carry the override
                result[source] = {"strategy": strategy, "auto": bool(auto)}
    except Exception:
        pass
    return result


def _forward_channel_strategy_over_sync(source: str, strategy: str | None, auto: bool) -> None:
    """Send a locally-made channel-strategy change to the paired node,
    whichever role this process has. No-op if sync isn't configured."""
    try:
        from forex_trader.sync import client as _sync_cli_mod
        cli = _sync_cli_mod.get_instance()
        if cli is not None:
            _schedule_coro(cli.propose_channel_strategy(source, strategy, auto))
            return
    except Exception as e:
        log.debug("[Sync] channel strategy forward (client) failed: %s", e)

    try:
        from forex_trader.sync import server as _sync_srv_mod
        srv = _sync_srv_mod.get_instance()
        if srv is not None:
            _schedule_coro(srv.broadcast_channel_strategy())
    except Exception as e:
        log.debug("[Sync] channel strategy forward (server) failed: %s", e)


def get_channel_strategy_rec(source: str) -> dict:
    """Return {strategy, reasoning, confidence, updated_at} for the last Claude recommendation."""
    canon = _canonical(source)
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT strategy, reasoning, confidence, updated_at FROM channel_strategy_rec WHERE source=?",
                (canon,),
            ).fetchone()
        if row:
            return {"strategy": row[0], "reasoning": row[1],
                    "confidence": row[2], "updated_at": row[3]}
    except Exception:
        pass
    return {"strategy": "", "reasoning": "", "confidence": 0.0, "updated_at": 0.0}


def set_channel_strategy_rec(source: str, strategy: str, reasoning: str, confidence: float) -> None:
    """Upsert a Claude strategy recommendation for a channel."""
    import time as _t
    canon = _canonical(source)
    with db() as conn:
        conn.execute(
            "INSERT INTO channel_strategy_rec (source, strategy, reasoning, confidence, updated_at) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(source) DO UPDATE SET strategy=excluded.strategy, "
            "  reasoning=excluded.reasoning, confidence=excluded.confidence, "
            "  updated_at=excluded.updated_at",
            (canon, strategy, reasoning, round(confidence, 3), _t.time()),
        )


def get_open_trade_count() -> int:
    """Count all open trades regardless of channel/source."""
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM vantage_simulated_trades WHERE status='open'"
            ).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def get_open_trade_count_for_channel(source: str) -> int:
    """Count open trades whose tg_source matches the given channel (all canonical variants)."""
    canon = _canonical(source)
    variants = [s for s, c in CANONICAL_CHANNELS.items() if c == canon]
    if not variants:
        variants = [source]
    placeholders = ",".join("?" * len(variants))
    try:
        with db() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM vantage_simulated_trades "
                f"WHERE status='open' AND tg_source IN ({placeholders})",
                variants,
            ).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def get_all_channel_strategy_settings() -> list:
    """Return merged, canonical channel stats for the Channel Strategy UI.

    Aggregates all variant source names (e.g. 'Telegram Auto (Gold Diggers VIP)',
    '1608388054') into the four canonical channels.  The strategy override is
    stored / read under the canonical name only.
    """
    # Merge all rows into canonical buckets (returned even when table has no rows)
    buckets: dict[str, dict] = {
        ch: {"source": ch, "strategy_override": None, "auto_strategy": False,
             "lot_mult": 1.0, "win_rate": 0.0, "sample_n": 0, "net_pnl": 0.0}
        for ch in CANONICAL_CHANNEL_ORDER
    }
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT source, strategy_override, auto_strategy, lot_mult, win_rate, sample_n, net_pnl "
                "FROM channel_performance ORDER BY source"
            ).fetchall()
    except Exception:
        return list(buckets.values())
    for r in rows:
        canon = _canonical(r[0])
        if canon not in buckets:
            continue  # skip manual_market, Manual Signal, etc.
        b = buckets[canon]
        # Strategy override comes from the canonical row only (not variants)
        if r[0] == canon:
            b["strategy_override"] = r[1]
            b["auto_strategy"] = bool(r[2])
        # Aggregate stats
        n_new = int(r[5] or 0)
        n_old = int(b["sample_n"])
        if n_new > 0:
            # Weighted average win rate
            wr_new = float(r[4] or 0)
            if n_old == 0:
                b["win_rate"] = wr_new
            else:
                b["win_rate"] = round(
                    (b["win_rate"] * n_old + wr_new * n_new) / (n_old + n_new), 1
                )
            b["sample_n"] += n_new
        b["net_pnl"] = round(b["net_pnl"] + float(r[6] or 0), 2)

    return [buckets[ch] for ch in CANONICAL_CHANNEL_ORDER]

    # (unreachable fallback)
    return []


# ── Global Circuit Breaker ────────────────────────────────────────────────────
# State is persisted in vantage_risk_settings so it survives restarts.
# Fields (auto-migrated by _ensure_settings_cols):
#   circuit_breaker_enabled        INTEGER  0/1
#   circuit_breaker_losses         INTEGER  consecutive live losses to trigger
#   circuit_breaker_cooldown_mins  INTEGER  minutes the CB stays active
#   circuit_breaker_active_until   REAL     unix timestamp when CB expires (0 = off)
#   circuit_breaker_consec_losses  INTEGER  running count of consecutive losses


def get_circuit_breaker_state() -> dict:
    """Return current CB state. is_active is authoritative."""
    rs  = get_risk_settings()
    now = time.time()
    enabled      = bool(rs.get("circuit_breaker_enabled", 0))
    active_until = float(rs.get("circuit_breaker_active_until", 0) or 0)
    is_active    = enabled and active_until > now
    return {
        "enabled":         enabled,
        "losses_threshold": int(rs.get("circuit_breaker_losses", 3) or 3),
        "cooldown_mins":   int(rs.get("circuit_breaker_cooldown_mins", 60) or 60),
        "active_until":    active_until,
        "consec_losses":   int(rs.get("circuit_breaker_consec_losses", 0) or 0),
        "is_active":       is_active,
        "remaining_secs":  max(0.0, active_until - now) if is_active else 0.0,
    }


def record_live_trade_outcome(won: bool) -> dict:
    """Update consecutive-loss counter after a live MT5 trade closes.

    On a win/BE, resets the counter.  On a loss, increments it and triggers
    the cooldown when the threshold is reached.  Returns the new CB state.
    """
    rs        = get_risk_settings()
    enabled   = bool(rs.get("circuit_breaker_enabled", 0))
    if not enabled:
        return get_circuit_breaker_state()

    consec    = int(rs.get("circuit_breaker_consec_losses", 0) or 0)
    threshold = int(rs.get("circuit_breaker_losses", 3) or 3)
    cooldown  = int(rs.get("circuit_breaker_cooldown_mins", 60) or 60)

    just_triggered = False
    if won:
        update_risk_settings({"circuit_breaker_consec_losses": 0})
    else:
        consec += 1
        updates: dict = {"circuit_breaker_consec_losses": consec}
        if threshold > 0 and consec >= threshold:
            updates["circuit_breaker_active_until"]  = time.time() + cooldown * 60
            updates["circuit_breaker_consec_losses"] = 0  # reset after trigger
            just_triggered = True
        update_risk_settings(updates)

    state = get_circuit_breaker_state()
    # Distinguishes "this call is the one that tripped it" from "it was
    # already active from an earlier trigger and this loss just closed
    # while the cooldown was still running" — callers alerting on trigger
    # need this or they'd re-notify on every loss that happens to close
    # during an already-active cooldown, not just the one that caused it.
    state["just_triggered"] = just_triggered
    return state


def reset_circuit_breaker() -> None:
    """Manually clear an active circuit breaker and reset the loss counter."""
    update_risk_settings({
        "circuit_breaker_active_until":  0.0,
        "circuit_breaker_consec_losses": 0,
    })


def set_channel_paused(source: str, paused: bool) -> None:
    """Manually pause/resume a channel; marks manual_override so auto-recompute
    won't flip it back."""
    import time as _t
    with db() as conn:
        conn.execute(
            "INSERT INTO channel_performance (source, paused, manual_override, updated_at) "
            "VALUES (?,?,1,?) "
            "ON CONFLICT(source) DO UPDATE SET paused=excluded.paused, "
            "  manual_override=1, updated_at=excluded.updated_at",
            (source, 1 if paused else 0, _t.time()),
        )


def get_channel_performance_map() -> dict:
    """Return {source: {lot_mult, paused, manual_override}} for the scorecard UI."""
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT source, lot_mult, paused, manual_override FROM channel_performance"
            ).fetchall()
        return {r[0]: {"lot_mult": float(r[1] or 1.0), "paused": bool(r[2]),
                       "manual_override": bool(r[3])} for r in rows}
    except Exception:
        return {}


def save_email_config(updates: dict) -> None:
    data = {**updates, "updated_at": time.time()}
    set_clause = ", ".join(f"{k}=?" for k in data)
    with db() as conn:
        conn.execute(
            f"UPDATE email_config SET {set_clause} WHERE id=1",
            list(data.values()),
        )


def get_app_config(key: str) -> Optional[str]:
    try:
        with db() as conn:
            row = conn.execute("SELECT value FROM app_config WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def set_app_config(key: str, value: str) -> None:
    try:
        with db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key,value) VALUES (?,?)", (key, value)
            )
    except Exception as e:
        log.debug("app_config set error: %s", e)


def get_cached_spreads(position_ids: list[int]) -> dict[int, dict]:
    """{position_id: {spread_price, spread_points, spread_cost_usd}} for already-computed tickets."""
    if not position_ids:
        return {}
    try:
        with db() as conn:
            placeholders = ",".join("?" * len(position_ids))
            rows = conn.execute(
                f"SELECT position_id, spread_price, spread_points, spread_cost_usd "
                f"FROM trade_spread_cache WHERE position_id IN ({placeholders})",
                position_ids,
            ).fetchall()
        return {
            r[0]: {"spread_price": r[1], "spread_points": r[2], "spread_cost_usd": r[3]}
            for r in rows
        }
    except Exception:
        return {}


def cache_spread(position_id: int, spread_price: float, spread_points: float, spread_cost_usd: float) -> None:
    try:
        with db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO trade_spread_cache "
                "(position_id, spread_price, spread_points, spread_cost_usd, computed_at) "
                "VALUES (?,?,?,?,?)",
                (position_id, spread_price, spread_points, spread_cost_usd, time.time()),
            )
    except Exception as e:
        log.debug("cache_spread error: %s", e)


def get_effective_strategy(rs: dict) -> tuple[str, bool]:
    """
    Return (effective_strategy_key, is_ooh_active).

    When Out of Hours is enabled and the current UTC time/date falls inside the
    configured window, the OOH strategy is returned and is_ooh_active=True.
    Otherwise the base trade_strategy is returned with is_ooh_active=False.

    The time window can span midnight (e.g. 22:00-07:00).
    The optional date range (ooh_date_from / ooh_date_to, ISO format YYYY-MM-DD)
    activates OOH all day on every date within the range — useful for holidays.
    """
    from datetime import datetime, date as _date, timezone as _tz

    base = rs.get("trade_strategy", "scale_out") or "scale_out"

    if not bool(rs.get("ooh_enabled", 0)):
        return base, False

    start_str     = rs.get("ooh_start_time", "22:00") or "22:00"
    end_str       = rs.get("ooh_end_time",   "07:00") or "07:00"
    ooh_strat     = rs.get("ooh_strategy",   "conservative") or "conservative"
    date_from_str = rs.get("ooh_date_from",  "") or ""
    date_to_str   = rs.get("ooh_date_to",    "") or ""

    try:
        now = datetime.now(_tz.utc)

        # Date-range filter: when active, OOH only applies on dates within the range.
        # If today is outside the range, OOH is inactive regardless of time.
        # If the date range is not active, the time window applies every day.
        if bool(rs.get("ooh_date_active", 0)) and date_from_str and date_to_str:
            try:
                d_from = _date.fromisoformat(date_from_str)
                d_to   = _date.fromisoformat(date_to_str)
                if not (d_from <= now.date() <= d_to):
                    return base, False
            except ValueError:
                return base, False

        # Daily time-window check
        cur = now.hour * 60 + now.minute
        sh, sm = (int(x) for x in start_str.split(":"))
        eh, em = (int(x) for x in end_str.split(":"))
        s = sh * 60 + sm
        e = eh * 60 + em
        in_window = (cur >= s or cur < e) if s >= e else (s <= cur < e)
        if in_window:
            return ooh_strat, True
    except Exception:
        pass
    return base, False


# ── MT5 credentials — always stored in the demo DB (env-independent) ─────────

def _master_creds_path() -> str:
    from forex_trader.config import DATA_DIR
    return str(DATA_DIR / "forex_trader_demo.db")


# Columns holding secrets — encrypted at rest via core.secrets (Fernet, key in
# OS keychain). get/save translate transparently so callers only ever see
# plaintext; legacy plaintext rows are upgraded on first read.
_CRED_SECRET_COLS = ("password_enc", "live_password_enc")


def get_mt5_credentials() -> dict:
    """Read MT5 credentials from the permanent demo DB regardless of active env.
    Secret columns are decrypted before returning; plaintext legacy values are
    re-saved encrypted the first time they are seen."""
    import sqlite3 as _sq
    try:
        conn = _sq.connect(_master_creds_path(), check_same_thread=False)
        conn.row_factory = _sq.Row
        row = conn.execute("SELECT * FROM mt5_credentials WHERE id=1").fetchone()
        conn.close()
        creds = dict(row) if row else {}
    except Exception:
        return {}

    try:
        from forex_trader.core import secrets as _sec
        legacy = {}
        for col in _CRED_SECRET_COLS:
            val = creds.get(col) or ""
            if val and not _sec.is_encrypted(val):
                legacy[col] = val          # plaintext row — upgrade below
            creds[col] = _sec.decrypt(val)
        if legacy:
            save_mt5_credentials(legacy)   # save_mt5_credentials encrypts
    except Exception as e:
        logging.getLogger(__name__).warning("[DB] credential decrypt failed: %s", e)
    return creds


def save_mt5_credentials(updates: dict) -> None:
    """Write MT5 credentials to the permanent demo DB regardless of active env.
    Secret columns are encrypted before hitting disk."""
    import sqlite3 as _sq
    try:
        from forex_trader.core import secrets as _sec
        updates = {
            k: (_sec.encrypt(v) if k in _CRED_SECRET_COLS and v else v)
            for k, v in updates.items()
        }
    except Exception as e:
        logging.getLogger(__name__).warning("[DB] credential encrypt failed: %s", e)
    conn = _sq.connect(_master_creds_path(), check_same_thread=False)
    try:
        sc = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE mt5_credentials SET {sc} WHERE id=1", list(updates.values())
        )
        conn.commit()
    finally:
        conn.close()


def _bridge_creds_path() -> str:
    """Return the macOS path to bridge_credentials.json.

    Lives in the user data directory (outside the project folder) so that
    distributing a new version of the app never ships credentials.
    The Wine bridge reads the same file via the Z: drive mount; the launcher
    script converts this path and passes it as BRIDGE_CREDS_PATH.
    """
    from forex_trader.config import USER_DATA_DIR
    return str(USER_DATA_DIR / "bridge_credentials.json")


def sync_bridge_credentials_file(env: str) -> bool:
    """
    Write the correct credentials for `env` directly to bridge_credentials.json
    so the bridge picks them up on the next (re)start.  Returns True on success.
    """
    import json
    creds = get_mt5_credentials()
    if env == "live":
        login    = int(creds.get("live_login") or 0)
        password = creds.get("live_password_enc") or ""
        server   = (creds.get("live_server") or "").strip()
    else:
        login    = int(creds.get("login") or 0)
        password = creds.get("password_enc") or ""
        server   = (creds.get("server") or "").strip()

    if not login or not password or not server:
        return False
    try:
        payload: dict = {"login": login, "password": password, "server": server}
        # Include terminal_path so the bridge can pass it to mt5.initialize() and
        # attach to the existing terminal rather than launching a new instance.
        if env == "live":
            tp = (creds.get("live_terminal_path") or "").strip()
        else:
            tp = (creds.get("terminal_path") or "").strip()
        if tp:
            payload["terminal_path"] = tp
        creds_file = _bridge_creds_path()
        with open(creds_file, "w") as f:
            json.dump(payload, f)
        # The bridge needs plaintext, but nothing else does — owner-only perms.
        try:
            os.chmod(creds_file, 0o600)
        except OSError:
            pass
        return True
    except Exception as e:
        log.warning("sync_bridge_credentials_file failed: %s", e)
        return False


# ── Channel parser config ─────────────────────────────────────────────────────

def get_channel_parser_config(channel_name: str) -> Optional[dict]:
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT * FROM channel_parser_config WHERE channel_name=?", (channel_name,)
            ).fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def get_all_channel_parser_configs() -> list[dict]:
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT * FROM channel_parser_config ORDER BY channel_name"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def save_channel_parser_config(
    channel_name: str,
    parser_format: str,
    signal_prefix: str,
    instant_entry_enabled: bool,
    enabled: bool,
    notes: str,
) -> None:
    now = time.time()
    with db() as conn:
        conn.execute(
            """INSERT INTO channel_parser_config
               (channel_name, parser_format, signal_prefix, instant_entry_enabled,
                enabled, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(channel_name) DO UPDATE SET
               parser_format=excluded.parser_format,
               signal_prefix=excluded.signal_prefix,
               instant_entry_enabled=excluded.instant_entry_enabled,
               enabled=excluded.enabled,
               notes=excluded.notes,
               updated_at=excluded.updated_at""",
            (channel_name, parser_format, signal_prefix,
             int(instant_entry_enabled), int(enabled), notes, now, now),
        )


# ── Unrecognised messages ─────────────────────────────────────────────────────

def save_unrecognised_message(channel_name: str, tg_message_id: str, raw_text: str) -> int:
    with db() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO channel_unrecognised_messages
               (channel_name, tg_message_id, raw_text, received_at, status)
               VALUES (?,?,?,?,?)""",
            (channel_name, tg_message_id, raw_text, time.time(), "pending"),
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute(
            "SELECT id FROM channel_unrecognised_messages WHERE tg_message_id=?",
            (tg_message_id,),
        ).fetchone()
        return row[0] if row else 0


def update_unrecognised_message(
    unrec_id: int,
    claude_analysis: Optional[str] = None,
    resolution: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    updates: dict = {}
    if claude_analysis is not None:
        updates["claude_analysis"] = claude_analysis
    if resolution is not None:
        updates["resolution"] = resolution
        updates["resolved_at"] = time.time()
    if status is not None:
        updates["status"] = status
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    with db() as conn:
        conn.execute(
            f"UPDATE channel_unrecognised_messages SET {set_clause} WHERE id=?",
            list(updates.values()) + [unrec_id],
        )


def get_pending_unrecognised_messages(limit: int = 50) -> list[dict]:
    try:
        with db() as conn:
            rows = conn.execute(
                """SELECT * FROM channel_unrecognised_messages
                   WHERE status='pending'
                   ORDER BY received_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_all_unrecognised_messages(limit: int = 200) -> list[dict]:
    try:
        with db() as conn:
            rows = conn.execute(
                """SELECT * FROM channel_unrecognised_messages
                   ORDER BY received_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ── Learned rules ─────────────────────────────────────────────────────────────

def get_channel_learned_rules(channel_name: Optional[str] = None) -> list[dict]:
    try:
        with db() as conn:
            if channel_name:
                rows = conn.execute(
                    "SELECT * FROM channel_learned_rules WHERE channel_name=? ORDER BY id",
                    (channel_name,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM channel_learned_rules ORDER BY channel_name, id"
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def save_channel_learned_rule(
    channel_name: str,
    rule_type: str,
    pattern: str,
    action: str,
    notes: str,
    source_msg_id: Optional[str] = None,
) -> int:
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO channel_learned_rules
               (channel_name, rule_type, pattern, action, notes, created_at, source_msg_id)
               VALUES (?,?,?,?,?,?,?)""",
            (channel_name, rule_type, pattern, action, notes, time.time(), source_msg_id),
        )
        return cur.lastrowid


def save_synced_learned_rule(
    channel_name: str, rule_type: str, pattern: str, action: str,
    notes: str, source_msg_id: Optional[str],
) -> int:
    """Like save_channel_learned_rule(), but for rules arriving over the
    Local/Remote sync link (see sync/protocol.py MSG_LEARNED_RULE_SYNC) —
    idempotent on (channel_name, rule_type, source_msg_id) so a duplicate
    delivery of the same peer-approved rule doesn't create a second row."""
    with db() as conn:
        if source_msg_id:
            existing = conn.execute(
                "SELECT id FROM channel_learned_rules "
                "WHERE channel_name=? AND rule_type=? AND source_msg_id=?",
                (channel_name, rule_type, source_msg_id),
            ).fetchone()
            if existing:
                return existing["id"]
        cur = conn.execute(
            """INSERT INTO channel_learned_rules
               (channel_name, rule_type, pattern, action, notes, created_at, source_msg_id)
               VALUES (?,?,?,?,?,?,?)""",
            (channel_name, rule_type, pattern, action, notes, time.time(), source_msg_id),
        )
        return cur.lastrowid


def get_learned_parser_rules(channel_name: str) -> list[dict]:
    """ai_derived_parser rules for this channel, most recently created first —
    used by signal_parser.parse_with_learned_rules() to try deterministic
    matching before ever falling back to the AI extractor again."""
    return get_learned_rules_by_type(channel_name, "ai_derived_parser")


def get_learned_rules_by_type(channel_name: str, rule_type: str) -> list[dict]:
    """Generalised form of get_learned_parser_rules() — also used for
    rule_type='ai_derived_sl_adjust' (see signal_parser.check_sl_adjustment_rules)."""
    try:
        with db() as conn:
            rows = conn.execute(
                """SELECT * FROM channel_learned_rules
                   WHERE channel_name=? AND rule_type=?
                   ORDER BY id DESC""",
                (channel_name, rule_type),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def delete_channel_learned_rule(rule_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM channel_learned_rules WHERE id=?", (rule_id,))


# ── AI-recovered signal review (Telegram > Reader Logic > AI tab) ─────────────

def save_ai_recovered_signal(
    tg_message_id: str, channel_name: str, raw_text: str, parsed: dict,
    confidence: float, reasoning: str,
) -> None:
    """Upsert, not a plain insert: a Telegram edit can trigger the AI fallback
    a second time for the same tg_message_id (e.g. the first pass extracted a
    signal, then a later edit corrected a level) — refresh the still-unapproved
    row with the improved extraction rather than silently keeping the stale
    first pass forever. Once a row is approved (or a rule generated from it),
    leave it alone — the approved extraction is what generated the rule, so
    overwriting it here would make the review-tab row lie about what was
    actually approved."""
    try:
        with db() as conn:
            existing = conn.execute(
                "SELECT id, approved, rule_generated FROM ai_recovered_signals "
                "WHERE tg_message_id=?", (tg_message_id,),
            ).fetchone()
            if existing and (existing["approved"] or existing["rule_generated"]):
                return
            fields = (
                raw_text, parsed.get("direction"),
                parsed.get("entry_low"), parsed.get("entry_high"), parsed.get("stop_loss"),
                parsed.get("tp1"), parsed.get("tp2"), parsed.get("tp3"), parsed.get("tp4"),
                parsed.get("tp5"), parsed.get("tp6"), parsed.get("tp7"), parsed.get("tp8"),
                confidence, reasoning,
            )
            if existing:
                conn.execute(
                    """UPDATE ai_recovered_signals
                       SET raw_text=?, direction=?, entry_low=?, entry_high=?, stop_loss=?,
                           tp1=?, tp2=?, tp3=?, tp4=?, tp5=?, tp6=?, tp7=?, tp8=?,
                           confidence=?, reasoning=?
                       WHERE id=?""",
                    fields + (existing["id"],),
                )
            else:
                conn.execute(
                    """INSERT INTO ai_recovered_signals
                       (raw_text, direction, entry_low, entry_high, stop_loss,
                        tp1, tp2, tp3, tp4, tp5, tp6, tp7, tp8, confidence, reasoning,
                        tg_message_id, channel_name, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    fields + (tg_message_id, channel_name, time.time()),
                )
    except Exception as e:
        log.warning("save_ai_recovered_signal failed: %s", e)


def save_ai_recovered_sl_adjustment(
    tg_message_id: str, channel_name: str, raw_text: str,
    new_stop_loss: float, confidence: float, reasoning: str,
) -> None:
    """Same table, same upsert-while-unapproved rule as
    save_ai_recovered_signal() — a follow-up "Adjust SL to X" style message
    reviewed in the same AI tab, just with message_type='sl_adjustment' and
    only new_stop_loss populated (no direction/entry/TP fields, since this
    isn't a new entry)."""
    try:
        with db() as conn:
            existing = conn.execute(
                "SELECT id, approved, rule_generated FROM ai_recovered_signals "
                "WHERE tg_message_id=?", (tg_message_id,),
            ).fetchone()
            if existing and (existing["approved"] or existing["rule_generated"]):
                return
            if existing:
                conn.execute(
                    """UPDATE ai_recovered_signals
                       SET raw_text=?, new_stop_loss=?, confidence=?, reasoning=?,
                           message_type='sl_adjustment'
                       WHERE id=?""",
                    (raw_text, new_stop_loss, confidence, reasoning, existing["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO ai_recovered_signals
                       (raw_text, new_stop_loss, confidence, reasoning, message_type,
                        tg_message_id, channel_name, created_at)
                       VALUES (?,?,?,?,'sl_adjustment',?,?,?)""",
                    (raw_text, new_stop_loss, confidence, reasoning,
                     tg_message_id, channel_name, time.time()),
                )
    except Exception as e:
        log.warning("save_ai_recovered_sl_adjustment failed: %s", e)


def try_claim_sl_adjustment(tg_message_id: str, channel_name: str, new_stop_loss: float) -> bool:
    """Dedup guard for SimulationEngine._apply_sl_adjustment() — returns True
    (and records the claim) the first time this tg_message_id is seen, False
    on every subsequent call. Needed because neither the ai_derived_sl_adjust
    fast path nor the AI-fallback path have any other table tracking which
    messages were already actioned (unlike entry signals, which dedupe via
    vantage_tg_signals) — without this, a message sitting in the Telegram
    reader's message buffer keeps getting re-matched and re-applied on every
    scan cycle for as long as it stays buffered."""
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO sl_adjustment_applied "
                "(tg_message_id, channel_name, new_stop_loss, applied_at) VALUES (?,?,?,?)",
                (tg_message_id, channel_name, new_stop_loss, time.time()),
            )
            return cur.rowcount > 0
    except Exception as e:
        log.warning("try_claim_sl_adjustment failed: %s", e)
        return False


def _text_hash(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


def has_ai_fallback_check(tg_message_id: str, text: str) -> bool:
    """True if this exact (tg_message_id, text) has already been through
    SimulationEngine._try_ai_signal_fallback() with a definitive result —
    the dedup guard that stops chatter from being reclassified by a paid AI
    call on every scan cycle. See ai_fallback_checked table comment."""
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT 1 FROM ai_fallback_checked WHERE tg_message_id=? AND text_hash=?",
                (tg_message_id, _text_hash(text)),
            ).fetchone()
            return row is not None
    except Exception:
        return False


def record_ai_fallback_check(tg_message_id: str, text: str) -> None:
    """Call only after the AI call itself succeeded (any definitive result,
    including "not a signal") — deliberately not called on a transient
    exception, so a network blip gets retried next cycle instead of
    permanently giving up on a message."""
    try:
        with db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO ai_fallback_checked (tg_message_id, text_hash, checked_at) "
                "VALUES (?,?,?)",
                (tg_message_id, _text_hash(text), time.time()),
            )
    except Exception as e:
        log.warning("record_ai_fallback_check failed: %s", e)


def get_ai_recovered_signals(limit: int = 100) -> list[dict]:
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_recovered_signals ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def has_unreviewed_ai_recovered_signals() -> bool:
    """Cheap existence check for the Telegram nav tab's notification dot —
    avoids fetching full rows just to know whether any are pending."""
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT 1 FROM ai_recovered_signals WHERE approved=0 LIMIT 1"
            ).fetchone()
            return row is not None
    except Exception:
        return False


def mark_ai_recovered_signal_approved(row_id: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE ai_recovered_signals SET approved=1, approved_at=? WHERE id=?",
            (time.time(), row_id),
        )


def mark_ai_recovered_signal_rule_result(row_id: int, rule_id: Optional[int], note: str) -> None:
    with db() as conn:
        conn.execute(
            """UPDATE ai_recovered_signals
               SET rule_generated=?, rule_id=?, rule_gen_note=? WHERE id=?""",
            (1 if rule_id else 0, rule_id, note, row_id),
        )


def discard_ai_recovered_signal(row_id: int) -> None:
    """Remove a row from the Reader Logic > AI review queue with no further
    action — no rule generated, nothing approved. Used for entries the user
    doesn't want to review/act on (e.g. a misclassified or no-longer-relevant
    extraction)."""
    with db() as conn:
        conn.execute("DELETE FROM ai_recovered_signals WHERE id=?", (row_id,))


# ── AI-recovered signal peer sync (sync/protocol.py MSG_AI_RECOVERED_*) ──────
# Mirrors of the row_id-based mutators above, keyed by tg_message_id instead
# — the peer's local autoincrement id for the same message is unrelated to
# this node's, so approve/discard actions arriving over the sync link have
# to look the row up by its natural key (tg_message_id is UNIQUE).

def get_unresolved_ai_recovered_signals() -> list[dict]:
    """Full still-pending queue snapshot — used for MSG_AI_RECOVERED_PUSH,
    the periodic full-resync that also backfills anything a peer missed
    while disconnected (mirrors get_consolidated_trades for the ledger)."""
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_recovered_signals WHERE approved=0 ORDER BY created_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def mark_ai_recovered_signal_approved_by_tg_id(tg_message_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE ai_recovered_signals SET approved=1, approved_at=? WHERE tg_message_id=?",
            (time.time(), tg_message_id),
        )


def mark_ai_recovered_signal_rule_result_by_tg_id(
    tg_message_id: str, rule_generated: bool, note: str,
) -> None:
    """Mirrors the boolean/note outcome only — not the numeric rule_id, which
    is meaningless across nodes (each side generates and stores its own rule
    row via the separate MSG_LEARNED_RULE_SYNC channel, with its own id)."""
    with db() as conn:
        conn.execute(
            "UPDATE ai_recovered_signals SET rule_generated=? WHERE tg_message_id=?",
            (1 if rule_generated else 0, tg_message_id),
        )
        if note:
            conn.execute(
                "UPDATE ai_recovered_signals SET rule_gen_note=? WHERE tg_message_id=?",
                (note, tg_message_id),
            )


def discard_ai_recovered_signal_by_tg_id(tg_message_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM ai_recovered_signals WHERE tg_message_id=?", (tg_message_id,))


# ── Signal bus ────────────────────────────────────────────────────────────────
# Lightweight cross-engine awareness layer.  Each engine writes here when it
# generates a signal; all engines read here at ML-scoring time to get
# concurrent_agreement and conflict-suppression features.  Rows are auto-expired
# by the prune helper; the table never grows large.

def _ensure_signal_bus() -> None:
    """Idempotent: create the table if it was added after initial schema run."""
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_bus (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                engine        TEXT    NOT NULL,
                direction     TEXT    NOT NULL,
                confidence    REAL    NOT NULL DEFAULT 0.0,
                created_at    REAL    NOT NULL,
                expires_at    REAL    NOT NULL,
                is_still_open INTEGER NOT NULL DEFAULT 1,
                signal_id     INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_bus_exp ON signal_bus(expires_at)")
        # Migration: add new columns to existing tables
        for col, defn in [
            ("is_still_open", "INTEGER NOT NULL DEFAULT 1"),
            ("signal_id",     "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE signal_bus ADD COLUMN {col} {defn}")
            except Exception:
                pass  # column already exists


def write_signal_bus(
    engine: str,
    direction: str,
    confidence: float = 0.0,
    ttl_seconds: float = 300.0,
    signal_id: Optional[int] = None,
) -> int:
    """
    Record a signal on the shared bus. Returns the bus row id.
    TTL default reduced to 5 min (matches max scalp trade lifetime).
    Call close_bus_entry() when the originating signal closes so other engines
    see it as resolved immediately rather than waiting for TTL expiry.
    """
    try:
        _ensure_signal_bus()
        now = time.time()
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO signal_bus"
                "(engine,direction,confidence,created_at,expires_at,is_still_open,signal_id)"
                " VALUES(?,?,?,?,?,1,?)",
                (engine, direction.upper(), float(confidence), now, now + ttl_seconds, signal_id),
            )
            return cur.lastrowid or 0
    except Exception as _e:
        log.debug("[SignalBus] write error: %s", _e)
        return 0


def close_bus_entry(engine: str, signal_id: int) -> None:
    """
    Mark the bus entry for this engine+signal_id as no longer open.
    Call this as soon as the originating signal closes (SL/TP hit) so the
    conflict check clears immediately rather than waiting for TTL expiry.
    """
    try:
        _ensure_signal_bus()
        with db() as conn:
            conn.execute(
                "UPDATE signal_bus SET is_still_open=0 WHERE engine=? AND signal_id=?",
                (engine, signal_id),
            )
    except Exception as _e:
        log.debug("[SignalBus] close_bus_entry error: %s", _e)


def get_concurrent_signals(
    exclude_engine: str,
    window_seconds: float = 900.0,
) -> list[dict]:
    """
    Return active, still-open signals from all engines except the caller.
    is_still_open=0 entries (signal already closed) are excluded even if TTL has not expired.
    """
    try:
        _ensure_signal_bus()
        cutoff = time.time() - window_seconds
        with db() as conn:
            rows = conn.execute(
                "SELECT engine, direction, confidence, created_at FROM signal_bus"
                " WHERE engine != ? AND expires_at > ? AND created_at > ? AND is_still_open = 1",
                (exclude_engine, time.time(), cutoff),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_concurrent_agreement(engine: str, direction: str, window_seconds: float = 900.0) -> float:
    """
    Return cross-engine agreement score for use as an ML feature.
      +1.0  one or more other engines agree (same direction)
      -1.0  one or more other engines disagree (opposite direction)
       0.0  no concurrent signals from other engines
    Disagreement takes priority over agreement.
    """
    signals = get_concurrent_signals(exclude_engine=engine, window_seconds=window_seconds)
    if not signals:
        return 0.0
    direction_up = direction.upper()
    has_agree    = any(s["direction"] == direction_up for s in signals)
    has_disagree = any(s["direction"] != direction_up for s in signals)
    if has_disagree:
        return -1.0
    if has_agree:
        return 1.0
    return 0.0


def prune_signal_bus() -> None:
    """Delete expired rows. Call periodically (e.g. every 30 min from a tick loop)."""
    try:
        _ensure_signal_bus()
        with db() as conn:
            conn.execute("DELETE FROM signal_bus WHERE expires_at < ?", (time.time(),))
    except Exception:
        pass


# ── Data retention ──────────────────────────────────────────────────────────
# Per-node preference (app_config, not synced) for how long historical data
# is kept before being deleted. 0 (the default) means indefinite — nothing is
# ever deleted. This was added 2026-07 after confirming there was never any
# retention/pruning logic in this codebase at all; the account simply hadn't
# been running very long yet. Keeping "indefinite" as the default preserves
# that existing behaviour exactly — this feature is opt-in, not a new limit.

def get_data_retention_days() -> int:
    try:
        raw = get_app_config("data_retention_days")
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def set_data_retention_days(days: int) -> None:
    set_app_config("data_retention_days", str(max(0, int(days))))


def prune_historical_data() -> dict:
    """
    Delete data older than the configured retention window. No-op if
    retention is set to indefinite (0, the default).

    Only ever deletes rows that are already historical/resolved:
      - telegram_messages: pure log, age-only.
      - vantage_simulated_trades: status='closed' only — open trades are
        never touched regardless of age.
      - vantage_signals: status IN ('closed','expired') only — pending/
        active signals are never touched.
      - vantage_tg_signals, channel_unrecognised_messages,
        ai_recovered_signals: parse/review logs, age-only (the live trade
        state they may have produced lives in the two tables above, which
        have their own explicit status guards).
    """
    days = get_data_retention_days()
    if days <= 0:
        return {"pruned": False, "reason": "indefinite", "deleted": {}}

    cutoff_epoch = time.time() - days * 86400
    cutoff_iso = datetime.fromtimestamp(cutoff_epoch, tz=timezone.utc).isoformat()
    deleted: dict[str, int] = {}
    try:
        with db() as conn:
            for table, clause, param in (
                ("telegram_messages", "received_at < ?", cutoff_iso),
                ("vantage_simulated_trades", "status='closed' AND close_time < ?", cutoff_epoch),
                ("vantage_signals", "status IN ('closed','expired') AND created_at < ?", cutoff_epoch),
                ("vantage_tg_signals", "parsed_at < ?", cutoff_epoch),
                ("channel_unrecognised_messages", "received_at < ?", cutoff_epoch),
                ("ai_recovered_signals", "created_at < ?", cutoff_epoch),
            ):
                cur = conn.execute(f"DELETE FROM {table} WHERE {clause}", (param,))
                deleted[table] = cur.rowcount
    except Exception as e:
        log.warning("prune_historical_data failed: %s", e)
        return {"pruned": False, "reason": str(e), "deleted": deleted}

    return {"pruned": True, "retention_days": days, "deleted": deleted}


def has_conflict_on_bus(engine: str, direction: str, window_seconds: float = 600.0) -> bool:
    """True if another engine has an active signal in the OPPOSITE direction."""
    signals = get_concurrent_signals(exclude_engine=engine, window_seconds=window_seconds)
    direction_up = direction.upper()
    return any(s["direction"] != direction_up for s in signals)


def get_messages_for_research(group_ids: list[str], since_iso: str) -> list[dict]:
    """Telegram messages for the given group_ids received since since_iso
    (UTC ISO string) — feeds the nightly GD Copy research job. Includes
    has_media/media_type so the caller can decide which ones to fetch
    images for; does not itself touch Telegram, just the local log."""
    placeholders = ",".join("?" for _ in group_ids)
    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM telegram_messages WHERE group_id IN ({placeholders}) "
            f"AND received_at >= ? ORDER BY id ASC",
            (*group_ids, since_iso),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Local/Remote sync — consolidated ledger, active-trader flag, node config ──
# Additive only: this never touches the per-engine operational tables
# (bo_signals, test_signals, gdc_signals, vantage_simulated_trades). Those
# use autoincrement integer ids that would collide if two independent
# installs' rows were ever merged directly. consolidated_trades is a
# separate, append-only table keyed by (node_id, trade_id) — trade_id is
# already a UUID on every engine that pushes here, so cross-node collision
# is not possible.

def _ensure_sync_tables() -> None:
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consolidated_trades (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id      TEXT    NOT NULL,
                trade_id     TEXT    NOT NULL,
                engine       TEXT    NOT NULL,
                direction    TEXT    NOT NULL,
                strategy     TEXT,
                open_time    REAL,
                close_time   REAL,
                pnl_dollars  REAL,
                outcome      TEXT,
                received_at  REAL    NOT NULL,
                UNIQUE(node_id, trade_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_consolidated_close ON consolidated_trades(close_time)"
        )
        # tg_source (channel) + mt5_ticket — added after the initial ledger
        # design shipped without them. History's ticket->channel lookup is
        # keyed by mt5_ticket and built only from THIS node's own
        # vantage_simulated_trades, so a trade opened by the OTHER node
        # (real, same shared MT5 account, but no local record of it) showed
        # a blank channel. Both columns let history.py fall back to the
        # ledger for tickets it has no local record of.
        for col, defn in [
            ("tg_source",  "TEXT"),
            ("mt5_ticket", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE consolidated_trades ADD COLUMN {col} {defn}")
            except Exception:
                pass  # column already exists
        # max_tp_hit + rr — same cross-node gap as tg_source/mt5_ticket above:
        # History's Max TP Hit and R:R columns are built only from THIS node's
        # own vantage_simulated_trades, so a trade the OTHER node opened
        # showed blank for both, even though the underlying MT5 deal (and its
        # cost) is on the one shared account. max_tp_hit isn't known at the
        # original push_trade_closed() call (it's computed by
        # _max_tp_checker_loop 30+ min after close) — see that loop's
        # follow-up push, which relies on the same UNIQUE(node_id, trade_id)
        # upsert updating this row rather than creating a duplicate.
        for col, defn in [
            ("max_tp_hit", "TEXT"),
            ("rr",         "REAL"),
        ]:
            try:
                conn.execute(f"ALTER TABLE consolidated_trades ADD COLUMN {col} {defn}")
            except Exception:
                pass  # column already exists
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_consolidated_ticket ON consolidated_trades(mt5_ticket)"
        )


def get_or_create_node_id() -> str:
    """Stable random identifier for this install, generated once. Used to tag
    rows pushed into the other side's consolidated ledger."""
    existing = get_app_config("sync_node_id")
    if existing:
        return existing
    import uuid as _uuid
    node_id = _uuid.uuid4().hex[:12]
    set_app_config("sync_node_id", node_id)
    return node_id


def record_consolidated_trade(node_id: str, trade: dict) -> None:
    """Insert or update one closed-trade row in the consolidated ledger.
    Safe to call for both locally-originated trades and rows received from
    the other node over the sync channel — UNIQUE(node_id, trade_id) makes
    this idempotent, so re-delivery after a reconnect can't duplicate a row.

    Also the target of _max_tp_checker_loop's follow-up push once
    max_tp_hit is known (30+ min after the original close-time push, which
    can't include it yet) — the ON CONFLICT UPDATE only touches max_tp_hit
    when a real value is supplied, so that second, partial push can't
    clobber rr or any other field back to NULL."""
    _ensure_sync_tables()
    with db() as conn:
        conn.execute(
            """INSERT INTO consolidated_trades
               (node_id, trade_id, engine, direction, strategy, open_time,
                close_time, pnl_dollars, outcome, received_at, tg_source, mt5_ticket,
                max_tp_hit, rr)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(node_id, trade_id) DO UPDATE SET
                 close_time=excluded.close_time, pnl_dollars=excluded.pnl_dollars,
                 outcome=excluded.outcome, received_at=excluded.received_at,
                 tg_source=excluded.tg_source, mt5_ticket=excluded.mt5_ticket,
                 max_tp_hit=COALESCE(excluded.max_tp_hit, consolidated_trades.max_tp_hit),
                 rr=COALESCE(excluded.rr, consolidated_trades.rr)""",
            (node_id, trade["trade_id"], trade.get("engine", ""),
             trade.get("direction", ""), trade.get("strategy", ""),
             trade.get("open_time"), trade.get("close_time"),
             trade.get("pnl_dollars"), trade.get("outcome"), time.time(),
             trade.get("tg_source"), trade.get("mt5_ticket"),
             trade.get("max_tp_hit"), trade.get("rr")),
        )


def get_consolidated_ticket_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return ({mt5_ticket_str: tg_source}, {mt5_ticket_str: strategy},
    {mt5_ticket_str: direction}) from the consolidated ledger — i.e. from ALL
    paired nodes, not just this one. history.py merges this in as a fallback
    for tickets with no local vantage_simulated_trades row (trades the OTHER
    node opened)."""
    _ensure_sync_tables()
    with db() as conn:
        rows = conn.execute(
            "SELECT mt5_ticket, tg_source, strategy, direction FROM consolidated_trades "
            "WHERE mt5_ticket IS NOT NULL"
        ).fetchall()
    channel_map, strategy_map, direction_map = {}, {}, {}
    for mt5_ticket, tg_source, strategy, direction in rows:
        key = str(mt5_ticket)
        if tg_source:
            channel_map[key] = tg_source
        if strategy:
            strategy_map[key] = strategy
        if direction:
            direction_map[key] = direction
    return channel_map, strategy_map, direction_map


def get_consolidated_extra_maps() -> tuple[dict[str, str], dict[str, float]]:
    """Return ({mt5_ticket_str: max_tp_hit}, {mt5_ticket_str: rr}) from the
    consolidated ledger — same cross-node fallback purpose as
    get_consolidated_ticket_maps(), split out separately since these two
    columns were added later and populate at different times (rr at close,
    max_tp_hit 30+ min after)."""
    _ensure_sync_tables()
    with db() as conn:
        rows = conn.execute(
            "SELECT mt5_ticket, max_tp_hit, rr FROM consolidated_trades "
            "WHERE mt5_ticket IS NOT NULL AND (max_tp_hit IS NOT NULL OR rr IS NOT NULL)"
        ).fetchall()
    max_tp_map, rr_map = {}, {}
    for mt5_ticket, max_tp_hit, rr in rows:
        key = str(mt5_ticket)
        if max_tp_hit:
            max_tp_map[key] = max_tp_hit
        if rr is not None:
            rr_map[key] = rr
    return max_tp_map, rr_map


def get_consolidated_trades(days: int = 0) -> list[dict]:
    _ensure_sync_tables()
    cutoff = time.time() - days * 86400 if days > 0 else 0
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM consolidated_trades WHERE COALESCE(close_time,0) >= ? "
            "ORDER BY close_time DESC", (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_active_trader() -> str:
    """'local' or 'remote_vps'. Defaults to remote_vps — the VPS is the
    always-on trader unless this Mac has explicitly taken over."""
    return get_app_config("active_trader") or "remote_vps"


def set_active_trader(value: str) -> None:
    set_app_config("active_trader", value)


def is_remote_node() -> bool:
    """True iff this process is running in the VPS/remote-server sync role
    (sync_server_enabled) — a fixed physical-machine fact, independent of
    which side is currently the active trader or whether centralized signal
    generation is toggled on. Used to keep the Breakout, Bounce, and GD Copy
    analytical signal generators local-node-only unconditionally, rather than
    only as a side effect of centralized_signal_gen_enabled staying on (see
    should_generate_signals_here below, which is execution-routing-focused
    and stays conditional)."""
    return get_app_config("sync_server_enabled") == "1"


def should_generate_signals_here() -> bool:
    """False only when centralized_signal_gen_enabled is on AND this node is
    physically the VPS AND the VPS is currently the active trader (Remote
    mode) — i.e. signal generation has been centralized onto the Mac and
    this node should only execute trades forwarded to it, not analyze
    anything itself. Local mode and centralization-off both return True
    (today's behavior: this node generates as normal)."""
    rs = get_risk_settings()
    if not rs.get("centralized_signal_gen_enabled"):
        return True
    try:
        from forex_trader.sync import server as _sync_srv_mod
    except ImportError:
        return True
    if _sync_srv_mod.get_instance() is None:
        return True  # this is the Mac — always generate
    if get_active_trader() != "remote_vps":
        return True  # VPS is standing down anyway (Local mode) — unaffected
    return False


def get_stood_down_engines() -> list[str]:
    """Engines this node auto-paused because the OTHER node took over via
    STAND_DOWN — distinct from engines the local user disabled themselves,
    so RESUME only re-enables what sync stood down, never overriding a
    deliberate local on/off preference."""
    import json as _json
    raw = get_app_config("sync_stood_down_engines")
    try:
        return _json.loads(raw) if raw else []
    except Exception:
        return []


def set_stood_down_engines(names: list[str]) -> None:
    import json as _json
    set_app_config("sync_stood_down_engines", _json.dumps(names))


def generate_sync_token() -> str:
    """Generate a new random sync token, persist it encrypted (reusing the
    Fernet-at-rest pattern from core.secrets), and return the plaintext once
    so the operator can copy it into the other node's settings. Overwrites
    any previous token — do this once per node pairing, not per restart."""
    import secrets as _secrets
    from forex_trader.core import secrets as _sec
    token = _secrets.token_urlsafe(32)
    set_app_config("sync_token_enc", _sec.encrypt(token))
    return token


def get_sync_token() -> str:
    """Decrypt and return this node's persisted sync token, or '' if none
    has been generated yet."""
    from forex_trader.core import secrets as _sec
    enc = get_app_config("sync_token_enc") or ""
    return _sec.decrypt(enc) if enc else ""


# ── Equity curve helpers ──────────────────────────────────────────────────────

def get_equity_drawdown_pct() -> float:
    """
    Current drawdown from peak equity as a fraction [0, 1].
    Uses the simulation account balance and peak_balance if stored, or
    derives it from the recent trade P&L history.
    Returns 0.0 if equity data is unavailable.
    """
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT balance, peak_balance FROM vantage_simulation_account WHERE id=1"
            ).fetchone()
            if row and row["peak_balance"] and float(row["peak_balance"]) > 0:
                peak = float(row["peak_balance"])
                bal  = float(row["balance"])
                dd   = max(0.0, (peak - bal) / peak)
                return round(min(dd, 1.0), 4)
            # Fallback: derive from last 50 closed trades
            rows = conn.execute(
                "SELECT SUM(profit) as cumulative FROM ("
                "  SELECT profit FROM vantage_simulated_trades "
                "  WHERE status='closed' ORDER BY close_time DESC LIMIT 50"
                ")"
            ).fetchone()
            if rows and rows[0]:
                recent_pnl = float(rows[0])
                if recent_pnl < 0:
                    return round(min(abs(recent_pnl) / 1000.0, 1.0), 4)
    except Exception:
        pass
    return 0.0


# ── Regime detection helper ───────────────────────────────────────────────────

def get_regime_score(adx: float, atr: float, atr_avg: float = 0.0) -> float:
    """
    Classify current market regime as a normalised score [0, 1]:
      1.0  strongly trending   (ADX ≥ 40)
      0.75 trending            (ADX 28-40)
      0.5  mixed/volatile      (ADX 20-28 or ATR >> average)
      0.25 weakly ranging      (ADX 14-20)
      0.0  ranging/choppy      (ADX < 14)
    ATR expansion (atr / atr_avg > 1.5) promotes to volatile regardless of ADX.
    """
    if adx >= 40:
        regime = 1.0
    elif adx >= 28:
        regime = 0.75
    elif adx >= 20:
        regime = 0.5
    elif adx >= 14:
        regime = 0.25
    else:
        regime = 0.0

    # ATR spike → volatile regime
    if atr_avg > 0 and atr / atr_avg > 1.5:
        regime = max(regime, 0.5)

    return regime
