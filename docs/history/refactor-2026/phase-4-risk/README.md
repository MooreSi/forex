# Phase 4 — risk

**Status:** complete
**Done:** 2026-07-27

Seven modules to `backend/src/services/risk/`, all verified broker-free first
(the one grep hit in the schedule module was a docstring):

  core_db_risk_settings     -> risk_settings_repo.py   (the _rs_cache stays on the
                                                        database module, so the 119
                                                        test fixtures poking
                                                        db._rs_cache are untouched)
  core_db_circuit_breaker   -> circuit_breaker_repo.py
  core_db_custom_strategies -> custom_strategies_repo.py
  core_db_app_config        -> app_config_repo.py
  core_risk_governor        -> governor.py
  core_trading_schedule     -> schedule.py
  core_strategy_params      -> strategy_params.py       (its cache is registered with
                                                        database.init()'s invalidator
                                                        registry; registration moved
                                                        with the file)

First phase whose code can affect live behaviour, but only in the refuse-to-trade
direction: the governor, session gates and circuit breaker deny trades; nothing
here places or modifies one.

Knock-ons fixed in the same commit: the orphan detector's synthetic test
examples had been rewritten by the bulk sed (they referenced the moved modules
by name) and were rebuilt on modules still in core/; the sql ratchet entries for
governor/schedule/strategy_params are path renames of pre-existing inline SQL,
rebaselined as such and still on the burn-down list.
