# Phase 3 — notifications, ai, channels

**Status:** in progress
**Started:** 2026-07-27

Write-to-database, never-to-broker services. Each module is checked for broker
calls before moving, not assumed safe from its name — the check that caught
`orb_auto_execute` hiding in an "analytics" module in phase 2.

## Done

- [x] **notifications/** — `email_service.py` (946), `scheduler.py` (was
      core_email_scheduler), `repo.py` (was core_db_email). The one grep hit for
      a broker call was a dict-key read of an open-trade *count*. Thirteen
      importer files rewired; the multi-name form
      `from forex_trader.core import telegram_alerts, email_service` needed
      hand-splitting at four sites the mechanical rules could not touch.

## To do

- [x] **ai/** — five modules moved: claude_ai, provider (was ai_provider),
      signal_extractor, commentary_repo, recovered_repo. **core_ai_signal_fallback
      stays in core/**: the broker check found a real `bridge.modify_order` at
      line 232 (SL adjustment on a live position). Second real catch for that
      check after orb_auto_execute. recovered_repo carries its pre-existing
      3 unwrapped multi-write functions to the new path (rename, not growth).
- [ ] **channels/** — core_db_channel (644, splits along the transport/policy
      seam), core_db_channel_parser, core_db_learned_rules, core_db_unrecognised,
      channel_strategy_ai, ai_rule_generator.
- [ ] Baseline note: email_service.py carries its 946-line allowlist entry to its
      new path (path rename, not growth); scheduler.py's 2 SQL statements ditto.
      sync/server.py rose 1096 -> 1097 from an unavoidable import split — the
      documented legitimate-rise case.
