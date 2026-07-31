# Phase 5 — telegram transport + signals ingestion

**Status:** 5a done (transport); signals/ and the engine fat-method dissolves remain

## 5a — transport (done 2026-07-27)

Seven modules to `backend/src/services/telegram/`, broker-checked first:

  telegram_alerts             -> alerts.py            (54 importers rewired)
  core_db_telegram            -> repo.py
  telegram_reader             -> reader.py            (1,037 LOC; over-ceiling entry
                                                       carried as a path rename,
                                                       split deferred)
  core_logic_keywords         -> keywords.py
  core_logic_keyword_triggers -> keyword_triggers.py  (closes trades ONLY via an
                                                       injected close_trade_fn; no
                                                       broker import)
  core_bot_commands_readonly  -> bot_readonly.py
  core_bot_commands_infra     -> bot_infra.py

**Excluded by the broker check:** `core_bot_commands_trading` imports and calls
`open_trade` directly (cmd_activate, line 108). Third module the check has kept
out of a service package; it stays in core/ for phase 8.

Milestone crossed in this commit: **the orphan detector reports zero orphaned
functions** — the audit's opening headline of 456 LOC of extracted-but-dead code
is fully resolved (five deleted, two delegated, the trivial defaults moved out
with their services).

## Remaining

- [ ] signals/: signal_parser, core_signals, core_tg_signals, core_update_signal,
      core_pending_signal_activation, core_instant_entry/followup, the four
      core_scan_messages_* packs — each needs the broker check; several take
      injected open/close callbacks and should pass.
- [ ] Dissolve engine.py's `_scan_messages` (321 LOC) and `_bot_command_loop`.
- [ ] Split reader.py under the 800 ceiling.
