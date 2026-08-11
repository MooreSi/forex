# 020 — Extract signal resolution

**Status:** Done (2026-07-20)
**Depends on:** 010
**Real-money surface:** none — pure computation and DB reads/writes to `vantage_signals` and
channel-scorecard tables; the one bridge touch (`get_tick`/`get_trading_balance`) is read-only.

## Decision

Extract into `core_signal_resolution.py` as a single plain async function taking `bridge`
explicitly. Reuses `core_risk_governor.check_pre_trade_filters`/`price_in_entry_range`/
`rg_size_and_check` (pack 1), `core_fees_sizing.suggest_lot_size` (pack 1),
`core_close_trade.get_trading_balance` (pack 10) instead of the `self.*` equivalents. Ports
`_gdvr_sl_dist`/`_adaptive_sl_dist`/`_adaptive_final_tp_dist` and the per-strategy point-
distance constants verbatim.

## Tests first (TDD)

- 010's suite, re-pointed at the new function -- but since 010 characterized through the FULL
  `open_trade_from_signal` (the split doesn't exist in `engine.py`), 020's surface tests call
  the new function directly and assert on its RETURNED resolved values (`strategy`, `lot_size`,
  `stop_loss_to_use`) instead of reading them back off a fake bridge's `place_order` call log --
  a more direct assertion, now that the split actually exists.

## What to do

1. Confirm 010's suite is green.
2. Create `core_signal_resolution.py`, porting the front-half logic 1:1 (drop `self`, take
   `bridge` explicitly, `dpm_candles` as an explicit parameter instead of `self._dpm_candles`).
   Returns `{sig, strategy, lot_size, stop_loss_to_use, tick}` instead of falling through into
   the atomic claim.
3. Write new surface tests calling the function directly, covering the same scenarios as 010.
4. Leave `engine.py` untouched -- same precedent as every prior pack.

## Acceptance

- New function's behavior matches 010's characterization (same gates, same resolved values for
  the same inputs).
- `engine.py` untouched.
- No real or demo MT5 order placed or modified (this pack's own scope touches the bridge for
  reads only).

## Notes

Created `forex_trader/core/core_signal_resolution.py` (358 lines, well under the 800-line
ceiling) -- 1:1 port of the front half of `open_trade_from_signal`, no logic changes. Ported
the 3 SL-distance helper functions and all point-distance constants verbatim.

**One self-caught bug during extraction (not present in `engine.py`, introduced and fixed
within this same task, never committed broken)**: my first draft read `starting_balance` from
`rs.get("starting_balance", 1000.0)` — but `starting_balance` isn't a `vantage_risk_settings`
field at all; the original reads `self._cfg.get("starting_balance", 1000.0)`, a different,
engine-instance-level config dict. Since `self._cfg` isn't derivable from the database, fixed
by adding `starting_balance: float = 1000.0` as an explicit parameter (same pattern as pack
1's `reset_simulation`/pack 8's `compute_performance`) instead of silently misreading it from
the wrong dict. Caught before writing any tests against it, by re-checking pack 10's
`get_trading_balance` signature.

Added `tests/core/test_signal_resolution_surface.py` (33 tests) — since the extraction split
point now genuinely exists (unlike 010, which had to infer resolved values from a fake
bridge's `place_order` call log), these tests call `resolve_open_trade_params()` directly and
assert on its returned dict — a cleaner, more direct equivalence proof. Full `tests/core/`
suite: 396/396 green (363 from packs 1-11 + 33 from this pack). Repo-wide: 727/729 green --
same 2 pre-existing `pytest-asyncio`-missing failures from earlier packs, unrelated.
`engine.py` untouched -- new function not yet wired back in. No real or demo MT5 order placed
or modified anywhere in this pack (bridge touched for reads only: `get_tick`/`get_account`).
