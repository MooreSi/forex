# Phase 5 — telegram transport + signals ingestion

**Status:** 5a + 5b done; engine fat-method dissolves remain

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

## 5b — signals ingestion (done 2026-07-27)

Eight modules to `backend/src/services/signals/`: parser, repo, tg_repo,
resolution, pending_activation, and three of the four scan_messages packs
(parse_classify, staleness, edit_reparse). Broker use in the package is
read-only (`bridge.get_tick`).

**Four more excluded by the broker check** — all make real `modify_order` or
`open_trade` calls and stay in core/ for the trading phases:
core_update_signal, core_instant_entry, core_instant_followup,
core_scan_messages_auto_execute. Seven modules total have now been kept out of
service packages by that check.

The orphan tests' synthetic examples were rewritten onto a fictional module
name (`core_zz_example`) after a bulk rewrite reached into them for the second
phase running — no future move can touch them now.

## Remaining

- [ ] Dissolve engine.py's `_scan_messages` (321 LOC) and `_bot_command_loop`.
- [ ] Split reader.py under the 800 ceiling.
- [ ] The four broker-calling ingestion modules move with phases 6-8.
